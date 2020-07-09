from dagster import check
from dagster.core.events import EngineEventData
from dagster.core.instance import DagsterInstance
from dagster.core.origin import PipelinePythonOrigin
from dagster.core.storage.pipeline_run import PipelineRun
from dagster.grpc.client import ephemeral_grpc_api_client
from dagster.grpc.server import ExecuteRunArgs
from dagster.serdes.ipc import (
    IPCErrorMessage,
    ipc_read_event_stream,
    open_ipc_subprocess,
    write_unary_input,
)
from dagster.utils import safe_tempfile_path


def cli_api_execute_run(output_file, instance, pipeline_origin, pipeline_run):
    check.str_param(output_file, 'output_file')
    check.inst_param(instance, 'instance', DagsterInstance)
    check.inst_param(pipeline_origin, 'pipeline_origin', PipelinePythonOrigin)
    check.inst_param(pipeline_run, 'pipeline_run', PipelineRun)

    from dagster.cli.api import ExecuteRunArgsLoadComplete

    with safe_tempfile_path() as input_file:
        write_unary_input(
            input_file,
            ExecuteRunArgs(
                pipeline_origin=pipeline_origin,
                pipeline_run_id=pipeline_run.run_id,
                instance_ref=instance.get_ref(),
            ),
        )

        parts = [
            pipeline_origin.executable_path,
            '-m',
            'dagster',
            'api',
            'execute_run',
            input_file,
            output_file,
        ]

        instance.report_engine_event(
            'About to start process for pipeline "{pipeline_name}" (run_id: {run_id}).'.format(
                pipeline_name=pipeline_run.pipeline_name, run_id=pipeline_run.run_id
            ),
            pipeline_run,
            engine_event_data=EngineEventData(marker_start='cli_api_subprocess_init'),
        )

        process = open_ipc_subprocess(parts)

        # we need to process this event in order to ensure that the called process loads the input
        event = next(ipc_read_event_stream(output_file))

        check.inst(event, ExecuteRunArgsLoadComplete)

        return process


def cli_api_execute_run_grpc(execute_run_args):
    check.inst_param(execute_run_args, 'execute_run_args', ExecuteRunArgs)

    instance = DagsterInstance.from_ref(execute_run_args.instance_ref)

    pipeline_run = instance.get_run_by_id(execute_run_args.pipeline_run_id)

    yield instance.report_engine_event(
        'About to start process for pipeline "{pipeline_name}" (run_id: {run_id}).'.format(
            pipeline_name=pipeline_run.pipeline_name, run_id=pipeline_run.run_id
        ),
        pipeline_run,
        engine_event_data=EngineEventData(marker_start='cli_api_subprocess_init'),
    )

    with ephemeral_grpc_api_client() as api_client:
        for event in api_client.execute_run(execute_run_args=execute_run_args):
            if isinstance(event, IPCErrorMessage):
                instance.report_engine_event(
                    event.message,
                    pipeline_run=pipeline_run,
                    engine_event_data=EngineEventData(
                        marker_end='cli_api_subprocess_init', error=event.serializable_error_info
                    ),
                )
                instance.report_run_failed(pipeline_run)
                return

            yield event
