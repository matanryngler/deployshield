# DX Improvements, GitHub App & Gemini Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve CI/CD reliability, reduce redundant workflow runs, add native Gemini CLI support, and polish documentation.

**Architecture:** Integrate GitHub App tokens for release-please, optimize workflow triggers/concurrency, create a native Gemini skill, and revamp README with badges and use cases.

**Tech Stack:** GitHub Actions (YAML), Markdown (Gemini Skill), Python (shared logic).

---

### Task 1: Integrate GitHub App for `release-please`

**Files:**
- Modify: `.github/workflows/release-please.yml`

- [ ] **Step 1: Update `release-please.yml` to use App Token**

```yaml
name: Release Please

on:
  push:
    branches:
      - main

permissions:
  contents: write
  pull-requests: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/create-github-app-token@v1
        id: app-token
        with:
          app-id: ${{ secrets.RELEASE_PLEASE_APP_ID }}
          private-key: ${{ secrets.RELEASE_PLEASE_PRIVATE_KEY }}
      - uses: googleapis/release-please-action@v4
        with:
          token: ${{ steps.app-token.outputs.token }}
```

- [ ] **Step 2: Commit changes**

```bash
git add .github/workflows/release-please.yml
git commit -m "ci: use GitHub App token for release-please to trigger CI"
```

---

### Task 2: Optimize CI Workflows (Run Names, Concurrency, Triggers)

**Files:**
- Modify: `.github/workflows/test.yml`
- Modify: `.github/workflows/lint-pr-title.yml`

- [ ] **Step 1: Update `test.yml` with run-name, concurrency, and smarter triggers**

```yaml
name: Tests
run-name: "Tests: ${{ github.event.pull_request.title || github.event.head_commit.message }}"

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    # ... existing job ...
```

- [ ] **Step 2: Update `lint-pr-title.yml` with run-name**

```yaml
name: "Lint PR Title"
run-name: "Lint PR Title: #${{ github.event.pull_request.number }} ${{ github.event.pull_request.title }}"
# ... rest of file ...
```

- [ ] **Step 3: Commit changes**

```bash
git add .github/workflows/test.yml .github/workflows/lint-pr-title.yml
git commit -m "ci: optimize workflows with run-names and concurrency"
```

---

### Task 3: Native Gemini CLI Support

**Files:**
- Create: `skills/gemini/SKILL.md`

- [ ] **Step 1: Create native Gemini skill referencing the validator**

```markdown
---
description: Production safety guardrails - prevents write/mutating operations on cloud, database, and deployment CLIs
globs:
  - "**/*.tf"
  - "**/*.tfvars"
  - "**/Pulumi.*"
  - "**/pulumi/**"
  - "**/k8s/**"
  - "**/kubernetes/**"
  - "**/helm/**"
  - "**/docker-compose.yml"
  - "**/Dockerfile"
  - "**/package.json"
---

# DeployShield for Gemini CLI

DeployShield is active. All Bash commands are validated before execution.

## Guarded CLIs
- Cloud: aws, gcloud, az, kubectl, helm, terraform, pulumi
- Database: psql, mysql, mongosh, redis-cli
- IaC: cdk, sam, serverless, ansible-playbook
- Other: vault, gh, docker, podman, npm, yarn, pnpm, cargo, twine, gem

## Safety Guidelines
- Use read-only commands (get, list, describe) to inspect state.
- Suggest --dry-run or plan where applicable.
- To allow writes in specific contexts, create a `.deployshield.json` file.

## Integration
This skill uses the core DeployShield validator via a PreToolUse hook.
```

- [ ] **Step 2: Update `hooks/hooks.json` if needed (Gemini CLI might need its own registration if not using the same hook file)**
Actually, Gemini CLI uses `PreToolUse` hooks defined in the same way if the plugin structure is followed.

- [ ] **Step 3: Commit changes**

```bash
git add skills/gemini/SKILL.md
git commit -m "feat: add native Gemini CLI support"
```

---

### Task 4: README Revamp & Polishing

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add badges and improve header**

```markdown
# 🛡️ DeployShield

[![Tests](https://github.com/matanryngler/deployshield/actions/workflows/test.yml/badge.svg)](https://github.com/matanryngler/deployshield/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/matanryngler/deployshield)](https://github.com/matanryngler/deployshield/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Support](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)

Production safety guardrails for **Claude Code** and **Gemini CLI**.
```

- [ ] **Step 2: Add cross-platform support documentation**

- [ ] **Step 3: Polish the CLI support tables and add a "Why DeployShield?" section**

- [ ] **Step 4: Commit changes**

```bash
git add README.md
git commit -m "docs: revamp README with badges and cross-platform support"
```
