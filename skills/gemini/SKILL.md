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
This skill uses the core DeployShield validator via a BeforeTool hook on the `run_shell_command` tool.
