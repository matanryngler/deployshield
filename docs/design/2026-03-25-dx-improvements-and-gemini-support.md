# Design: DX Improvements, GitHub App Integration & Gemini CLI Support

**Date:** 2026-03-25
**Status:** Draft

## Problem Statement
DeployShield needs better Developer Experience (DX), more robust CI/CD integration, and support for the Gemini CLI to expand its reach and usability.

## Proposed Solutions

### 1. GitHub App Integration for `release-please`
- **Goal**: Allow `release-please` PRs to automatically trigger CI checks (Lint/Test).
- **Implementation**:
    - Use `actions/create-github-app-token` in the `release-please.yml` workflow.
    - Leverage repo secrets `RELEASE_PLEASE_APP_ID` and `RELEASE_PLEASE_PRIVATE_KEY`.
    - Pass the resulting token to the `google-github-actions/release-please-action`.

### 2. CI Workflow Optimization
- **Goal**: Reduce redundant runs and improve visibility.
- **Implementation**:
    - Add `run-name` to all workflows for better traceability.
    - Optimize `on:` triggers to avoid duplicate runs on `push` when a PR exists.
    - Add `concurrency` groups to cancel outdated runs on the same branch.

### 3. Gemini CLI Native Support
- **Goal**: Enable DeployShield as an extension for Gemini CLI.
- **Implementation**:
    - Create `skills/gemini/SKILL.md` following Gemini CLI's native extension format.
    - Reference the existing `hooks/scripts/validate-cloud-command.py` to avoid code duplication.
    - Provide the same safety context and guardrails as the Claude Code version.

### 4. Documentation & README Revamp
- **Goal**: Give the project a professional, polished look.
- **Implementation**:
    - Add standard GitHub badges (Build, Release, License).
    - Add a "Core Features" section highlighting Recursive Safety and Context Awareness.
    - Document the cross-platform nature (Claude + Gemini).
    - Improve the layout of the CLI support tables.

## Security & Reliability
- Using a GitHub App is more secure than a PAT as it provides fine-grained, repo-specific permissions.
- The core validation engine remains zero-dependency and fast.

## Testing Strategy
- **Workflow Verification**: Manually trigger or push to verify `run-name` and concurrency.
- **Gemini Skill Verification**: Test the new skill locally using `gemini --skill-dir ./skills/gemini`.
- **README Check**: Verify all badges and links are functional.
