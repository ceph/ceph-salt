# Release Procedure

These are the steps to make a release for version `<version_number>`:

1. Make sure you are working on the current tip of the master branch.
2. Make sure the merged PRs of all important changes have the "Add To Changelog" label:
   https://github.com/ceph/ceph-salt/pulls?utf8=%E2%9C%93&q=is%3Apr+is%3Amerged+label%3A%22Add+To+Changelog%22+
3. Update `CHANGELOG.md` with all important changes introduced since previous version.
    - Create a new section `[<version_number>] <date YYYY-MM-DD>` and move all entries
      from the `[Unreleased]` section to the new section.
    - Make sure all github issues resolved in this release are referenced in the changelog.
    - Update the links at the bottom of the file.
4. Update version number in `ceph-salt.spec` to `Version: <version_number>`.
5. Create a commit with title `Bump to v<version_number>` containing the
   modifications to `CHANGELOG.md` made in the previous two steps.
6. Create an annotated tag for the above commit: `git tag -s -a v<version_number> -m"version <version_number>"`.
    - The message should be `version <version_number>`.
    - Using `git show v<version_number>`, review the commit message of the annotated tag.
      It should say: `version <version_number>`.
7. Push commit and tag to github repo: `git push <remote> master --tags`
8. Remove the "Add To Changelog" labels from all the merged PRs
9. Verify that no merged PRs have "Add To Changelog" label:
   https://github.com/ceph/ceph-salt/pulls?utf8=%E2%9C%93&q=is%3Apr+is%3Amerged+label%3A%22Add+To+Changelog%22+
