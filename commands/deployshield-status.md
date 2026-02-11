---
disable-model-invocation: true
---

# DeployShield Status

DeployShield is **active**. All Bash commands are validated before execution.

## Guarded CLIs by Category

### Cloud Providers
| CLI | Provider | Read-only examples |
|-----|----------|--------------------|
| `aws` | AWS | `describe-*`, `get-*`, `list-*`, `s3 ls`, `sts get-*` |
| `gcloud` | GCP | `describe`, `list`, `info`, `config list` |
| `az` | Azure | `show`, `list`, `get`, `account show` |
| `kubectl` | Kubernetes | `get`, `describe`, `logs`, `top`, `--dry-run` |
| `helm` | Helm | `list`, `get`, `show`, `status`, `template`, `--dry-run` |

### Databases
| CLI | Provider | Read-only examples |
|-----|----------|--------------------|
| `psql` | PostgreSQL | `-l`, `-c "SELECT ..."`, `-c "\dt"` |
| `mysql` | MySQL | `-e "SELECT ..."`, `-e "SHOW ..."` |
| `mongosh` / `mongo` | MongoDB | `--eval "db.col.find()"` |
| `redis-cli` | Redis | `GET`, `KEYS`, `SCAN`, `INFO`, `PING` |

### IaC & Deployment
| CLI | Provider | Read-only examples |
|-----|----------|--------------------|
| `terraform` | Terraform | `plan`, `show`, `output`, `validate`, `fmt`, `init` |
| `pulumi` | Pulumi | `preview`, `stack ls`, `config get`, `whoami` |
| `cdk` | AWS CDK | `diff`, `synth`, `list`, `doctor` |
| `sam` | AWS SAM | `validate`, `build`, `local`, `logs` |
| `serverless` / `sls` | Serverless | `info`, `print`, `package`, `invoke local` |
| `ansible-playbook` | Ansible | `--check`, `--syntax-check`, `--list-hosts` |

### Secrets, GitHub, Containers & Publishing
| CLI | Provider | Read-only examples |
|-----|----------|--------------------|
| `vault` | HashiCorp Vault | `read`, `list`, `status`, `kv get` |
| `gh` | GitHub CLI | `pr view/list`, `issue view/list`, `api` (GET) |
| `docker` / `podman` | Docker | `ps`, `images`, `logs`, `inspect`, `info` |
| `npm` / `yarn` / `pnpm` | npm | Everything except `publish`/`unpublish` |
| `twine` | PyPI | Everything except `upload` |
| `gem` | RubyGems | Everything except `push`/`yank` |
| `cargo` | Cargo | Everything except `publish` |

**Total: 27 guarded CLIs** — all using a default-deny model (if the CLI is recognized but the subcommand is not explicitly safe-listed, it is blocked).
