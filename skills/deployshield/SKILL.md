---
description: Cloud infrastructure safety guardrails - prevents write/mutating operations on cloud CLIs
globs:
  - "**/*.tf"
  - "**/*.tfvars"
  - "**/Pulumi.*"
  - "**/pulumi/**"
  - "**/*.yaml"
  - "**/*.yml"
  - "**/Dockerfile*"
  - "**/helm/**"
  - "**/charts/**"
  - "**/k8s/**"
  - "**/kubernetes/**"
  - "**/deploy/**"
  - "**/infrastructure/**"
  - "**/infra/**"
---

# DeployShield - Cloud Infrastructure Safety

DeployShield is active and guarding against accidental write/mutating operations on production cloud environments.

## Guarded Cloud CLIs

The following CLIs are monitored. **Only read-only commands are permitted:**

| CLI | Allowed Actions |
|-----|----------------|
| `aws` | `describe`, `get`, `list`, `wait`, `help`, `sts get-*`, `s3 ls`, `s3 cp` (download only), `configure list`, `sso login` |
| `gcloud` | `describe`, `list`, `info`, `help`, `config list`, `config get-value`, `auth list`, `auth print-*` |
| `az` | `show`, `list`, `get`, `help`, `account show`, `account list`, `ad signed-in-user show` |
| `kubectl` | `get`, `describe`, `logs`, `explain`, `api-resources`, `api-versions`, `cluster-info`, `version`, `config view`, `config get-*`, `config current-context`, `auth can-i`, `diff`, `top`, `wait` |
| `helm` | `list`, `ls`, `get`, `show`, `status`, `history`, `search`, `repo list`, `template`, `lint`, `verify`, `version`, `env` |
| `terraform` | `plan`, `show`, `output`, `state list`, `state show`, `state pull`, `validate`, `fmt`, `providers`, `version`, `graph`, `workspace list`, `workspace show`, `init` |
| `pulumi` | `preview`, `stack ls`, `stack select`, `config get`, `whoami`, `version`, `about` |

## Guidelines

- **Use read-only commands** to inspect infrastructure state before proposing changes
- **Suggest `--dry-run`** flags where applicable (e.g., `kubectl apply --dry-run=client`)
- **Recommend `terraform plan`** instead of `terraform apply` to preview changes
- **Recommend `pulumi preview`** instead of `pulumi up` to preview changes
- **Non-cloud commands** (npm, git, docker build, etc.) are not affected by DeployShield
- If a write operation is needed, explain what command would be required and let the user run it manually
