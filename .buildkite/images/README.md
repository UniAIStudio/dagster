Building out integration images is a two step process. One is the creation of a fixed
set of requirements that are checked in at .buildkite/images/integration. This is
typically done on your development machine. You then put up a diff with these
altered snapshot files and then instigate a build to build a fresh snapshot
image. See detailed instructions below.

The snapshot requirement files are locked at a given git hash (H) and a given
time (T) when the snapshots were built. The git hash H locks set set of dependencies
required. The time T sets the versions that were downloaded from the public pypi
at a particular time. The hash H is in the file .buildkite/images/integration_snapshot_builder/Dockerfile.
The time T is in .buildkite/defines.py in the INTEGRATION_IMAGE_VERSION variable.

## Publishing new integration images

1. Update the git hash in .buildkite/images/integration_snapshot_builder/Dockerfile.
2. Run the python script build_all_snapshots.py in .buildkite/images/build_all_snapshots.py.
   This will take awhile. The purpose of the scripts is to update the four files
   .buildkite/images/integration/snapshot-reqs-{python_version}.txt
3. Put up a diff with these planned changes.
4. Manually trigger a Buildkite Integration Image pipeline build for the diff tag - see for
   example: https://buildkite.com/dagster/integration-image-builds/builds/19. Find the diff tag
   in the diff itself by clicking "View In Buildkite" and there there is a link that looks like
   `phabricator/diff/7663`. Go to the integration pipeline at
   https://buildkite.com/dagster/integration-image-builds and click New Build.
   Hit "New Build", then make sure that the value for "Branch" is that value
   e.g. `phabricator/diff/7663` and the value for "Commit" is `HEAD`. ("Message" doesn't matter.)
5. After the images successfully publish to ECR, update the diff to set `INTEGRATION_IMAGE_VERSION`
   to the new version (check ECR for the version string, which is the YYYY-mm-ddTHHMMSS when the
   image was created.)
