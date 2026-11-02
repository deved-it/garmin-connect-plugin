# Automatic Releases Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan inline. Track steps with checkboxes.

**Goal:** Publish verified standalone archives automatically on version tag pushes.

**Architecture:** Preserve the existing native build matrix. A dependent Ubuntu job downloads its artifacts, verifies the four expected files, and uses GitHub CLI to create or update the release. Manual runs never publish.

**Tech Stack:** GitHub Actions YAML, Bash, GitHub CLI, SHA-256.

**Spec:** [Approved design](../specs/2026-11-02-automatic-releases-design.md).

## Task 1: Publish and document tagged builds

**Files:** `.github/workflows/release.yml`, `docs/INSTALL.md`.

- [x] Add a tag-push-only publication job with `needs: build`, job-scoped `contents: write`, and same-tag concurrency without cancellation.
- [x] Download and merge only `garmin-personal-plugin-*` artifacts from the current run. Require the macOS arm64 and Windows x64 ZIP/checksum pairs and verify checksums before contacting the release API.
- [x] Classify `v0.*` and version prerelease suffixes as prereleases. Pass the tag through an environment variable, not shell interpolation. Use `GH_TOKEN` and `GH_REPO` without checking out the source in the publication job.
- [x] Create missing releases as drafts with generated notes and an existing-tag check; upload the exact four files; publish only after upload succeeds. On reruns, reuse the existing release and replace same-name assets without deleting the release or tag.
- [x] Document tag-triggered publication, manual verification-only runs, version consistency, prereleases, unsigned packages and rerun asset replacement.
- [x] Run an Actions-aware linter and isolated shell checks with a stubbed `gh` command: new release, rerun, prerelease/stable classification, missing asset, checksum failure and upload failure. Confirm no real API writes occur during checks.
- [ ] Run `git diff --check`, review the scoped diff, commit and push on the user-requested `main`. Do not create a tag or claim an actual GitHub release was exercised.

## Verification record

- `actionlint` 1.7.12: passed for the release workflow (external ShellCheck disabled because it is not installed).
- YAML parsing and Bash syntax: passed.
- Nine isolated executions of the workflow's actual Bash block with a mock `gh`: passed. SHA-256 checks used real synthetic files; no GitHub API was contacted.
- Static assertions: passed for tag-push event gating, whole-matrix dependency, read/write permission separation and non-cancelling same-tag concurrency.
- Editor diagnostics: none for the workflow and installation guide.
- Native GitHub-hosted builds and actual release publication: not run as part of this change; no tag created.
