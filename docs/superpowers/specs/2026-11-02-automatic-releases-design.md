# Automatic standalone releases

## Approved scope

Extend the existing standalone build workflow to publish its verified archives
and SHA-256 files to GitHub Releases automatically after a version tag is pushed.
Do not create a tag or publish a release as part of implementing this change.

## Behavior

- Preserve the native macOS Apple Silicon and Windows x64 build matrix, tests,
  archive smoke tests and artifact uploads.
- Publish only for tag pushes matching the existing `v*` trigger. Manual workflow
  runs build verification artifacts only, even when launched against a tag.
- A separate publication job depends on the entire build matrix succeeding.
  Failed or cancelled builds must not publish a release.
- Collect both platforms' ZIPs and checksum files and require all four expected
  files before publishing. Publish no source workspace, credential files or
  unrelated artifacts.
- Create a release for the triggering tag with automatically generated notes.
  Tags beginning with `v0.` are prereleases. Tags containing a semantic-version
  prerelease suffix, such as `v1.0.0-rc.1`, are prereleases too. Other version tags
  are stable releases.
- Use the workflow's repository-scoped `GITHUB_TOKEN`; grant `contents: write`
  only to the publication job. Build jobs retain read-only repository access.
- Serialize publication for the same tag without cancelling an active run.
  A repeated successful run may update that tag's assets but must not create a
  duplicate release. Never delete an existing release or tag.

## Implementation boundaries

Modify `.github/workflows/release.yml` and maintainer release instructions in
`docs/INSTALL.md`. Keep the existing package layout, runtime and key storage
unchanged. This change does not add signing/notarization or certify native
ChatGPT UI compatibility. Source GitHub marketplace installations still use uv;
downloaded standalone archives remain the runtime-bundled installation path.

## Verification

Validate workflow syntax and expressions with a GitHub Actions-aware validator
where available. Check tag/manual publication gating, whole-matrix dependency,
job-scoped permissions, exact asset selection and prerelease classification.
Run `git diff --check` before committing. Record that actual cross-platform
builds and release publication require GitHub Actions execution; local static
validation alone is not proof that a release was published.

## Alternatives considered

Publishing independently in each platform job risks a partial release when one
platform fails. Publishing every manual run risks unintended releases during
verification. A single tag-only publication job avoids both behaviors.
