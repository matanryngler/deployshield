---
description: Cloud infrastructure and production safety guardrails - prevents write/mutating operations on cloud, database, and deployment CLIs
globs:
  - "**/*.tf"
  - "**/*.tfvars"
  - "**/Pulumi.*"
  - "**/pulumi/**"
  - "**/*.yaml"
  - "**/*.yml"
  - "**/Dockerfile*"
  - "**/docker-compose*"
  - "**/helm/**"
  - "**/charts/**"
  - "**/k8s/**"
  - "**/kubernetes/**"
  - "**/deploy/**"
  - "**/infrastructure/**"
  - "**/infra/**"
  - "**/ansible/**"
  - "**/playbooks/**"
  - "**/*.sql"
  - "**/migrations/**"
  - "**/.github/workflows/**"
---

# DeployShield - Production Safety Guardrails

DeployShield is active and guarding against accidental write/mutating operations on production environments.

## Guarded CLIs

The following CLIs are monitored. **Only read-only commands are permitted:**

### Cloud Providers

| CLI | Allowed Actions |
|-----|----------------|
| `aws` | `describe`, `get`, `list`, `wait`, `help`, `sts get-*`, `s3 ls`, `s3 cp` (download only), `configure list`, `sso login` |
| `gcloud` | `describe`, `list`, `info`, `help`, `config list`, `config get-value`, `auth list`, `auth print-*` |
| `az` | `show`, `list`, `get`, `help`, `account show`, `account list`, `ad signed-in-user show` |
| `kubectl` | `get`, `describe`, `logs`, `explain`, `api-resources`, `api-versions`, `cluster-info`, `version`, `config view`, `config get-*`, `config current-context`, `auth can-i`, `diff`, `top`, `wait`, any command with `--dry-run` |
| `helm` | `list`, `ls`, `get`, `show`, `status`, `history`, `search`, `repo list`, `template`, `lint`, `verify`, `version`, `env`, any command with `--dry-run` |

### Databases

| CLI | Allowed Actions |
|-----|----------------|
| `psql` | `-l` (list databases), `-c` with `SELECT`/`SHOW`/`DESCRIBE`/`EXPLAIN`/`\d` commands |
| `mysql` | `-e` with `SELECT`/`SHOW`/`DESCRIBE`/`EXPLAIN` queries |
| `mongosh` | `--eval` with `.find()`, `.count()`, `.stats()`, `.explain()`, `show` commands |
| `redis-cli` | `GET`, `KEYS`, `SCAN`, `INFO`, `PING`, `TTL`, `HGETALL`, `ZRANGE`, and other read commands |

### IaC & Deployment Tools

| CLI | Allowed Actions |
|-----|----------------|
| `terraform` | `plan`, `show`, `output`, `state list`, `state show`, `state pull`, `validate`, `fmt`, `providers`, `version`, `graph`, `workspace list`, `workspace show`, `init` |
| `pulumi` | `preview`, `stack ls`, `stack select`, `config get`, `whoami`, `version`, `about` |
| `cdk` | `diff`, `synth`, `list`, `doctor`, `version` |
| `sam` | `validate`, `build`, `local`, `logs`, `list` |
| `serverless`/`sls` | `info`, `print`, `package`, `invoke local` |
| `ansible-playbook` | Only with `--check`, `--syntax-check`, `--list-hosts`, `--list-tasks` |

### Secrets, GitHub, Containers & Publishing

| CLI | Allowed Actions |
|-----|----------------|
| `vault` | `read`, `list`, `status`, `version`, `login`, `token lookup`, `kv get` |
| `gh` | `pr view/list`, `issue view/list`, `api` (GET), `repo view/list/clone`, `auth`, `search` |
| `docker`/`podman` | `ps`, `images`, `logs`, `inspect`, `info`, `version`, `stats`, `compose ps/logs` |
| `npm`/`yarn`/`pnpm` | Everything **except** `publish`/`unpublish` |
| `twine` | Everything except `upload` |
| `gem` | Everything except `push`/`yank` |
| `cargo` | Everything except `publish` |

## Guidelines

- **Use read-only commands** to inspect state before proposing changes
- **Suggest `--dry-run`** flags where applicable (e.g., `kubectl apply --dry-run=client`)
- **Recommend `terraform plan`** instead of `terraform apply` to preview changes
- **Recommend `pulumi preview`** instead of `pulumi up` to preview changes
- **Recommend `ansible-playbook --check`** instead of running playbooks directly
- **Recommend `cdk diff`** instead of `cdk deploy` to preview changes
- **Use `SELECT` queries** to inspect database state, never run DDL/DML directly
- If a write operation is needed, explain what command would be required and let the user run it manually
