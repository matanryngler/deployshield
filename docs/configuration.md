# Configuration Guide

DeployShield's behavior can be customized using a JSON configuration file. By default, DeployShield blocks all write/mutating operations for its supported CLIs. Using a configuration file allows you to conditionally allow these operations based on your current environment context.

## Config File Location

DeployShield searches for a configuration file in the following order of precedence:

1.  **Environment Variable**: The path specified in the `DEPLOYSHIELD_CONFIG` environment variable.
2.  **Current Working Directory**: A `.deployshield.json` file in the directory where the command is executed.
3.  **User Home Directory**: A `.deployshield.json` file in your home directory (`~/.deployshield.json`).

If no configuration file is found, DeployShield defaults to **blocking all write operations** for guarded CLIs.

## Configuration Schema

The configuration file is a JSON object where keys are the CLI binary names and values are lists of patterns that represent "blocked" contexts.

```json
{
  "cli-name": ["pattern1", "pattern2", ...]
}
```

### Context Patterns

- **Format**: Patterns use standard Unix shell-style wildcards via Python's `fnmatch`.
- **`*`**: Matches everything.
- **`?`**: Matches any single character.
- **`[seq]`**: Matches any character in `seq`.
- **`[!seq]`**: Matches any character not in `seq`.
- **Case Sensitivity**: Patterns are case-sensitive.

### Matching Logic

1.  **Provider Check**: If a CLI is not mentioned in the config file, it remains **fully blocked** (writes are always denied).
2.  **Context Detection**: DeployShield attempts to detect the current context (e.g., K8s context name, AWS profile name).
3.  **Pattern Match**:
    - If the detected context matches **any** pattern in the list, the command is **blocked** if it's a write operation.
    - If the context does **not** match any pattern, the command is **allowed**.
    - If the list is empty (`[]`), the CLI is **never blocked** (DeployShield is effectively disabled for that provider).

## Context Detection Reference

DeployShield automatically detects context for the following providers:

| CLI | Detected Context | Logic |
| :--- | :--- | :--- |
| `kubectl` | Kube Context | `--context` flag or `current-context` from `KUBECONFIG` |
| `helm` | Kube Context | `--kube-context` flag or `current-context` from `KUBECONFIG` |
| `aws` | AWS Profile | `--profile` flag, `AWS_PROFILE` env prefix, or `AWS_PROFILE` env var |
| `terraform` | Workspace | `TF_WORKSPACE` env var or `.terraform/environment` file |
| `gcloud` | GCP Project | `--project` flag or `CLOUDSDK_CORE_PROJECT` env var |
| `az` | Subscription | `--subscription` flag or `AZURE_SUBSCRIPTION_ID` env var |
| `pulumi` | Stack | `--stack`/`-s` flag |

*Note: For other providers or when detection fails, DeployShield defaults to **Blocked** for security.*

## Advanced Examples

### 🧪 Granular Kubernetes Control
Block only specific production clusters while allowing access to everything else.
```json
{
  "kubectl": ["prod-us-east-1", "prod-us-west-2", "billing-production"],
  "helm": ["prod-*"]
}
```

### ☁️ AWS Multi-Profile Setup
Block writes on your `production` and `staging` profiles but allow them on `sandbox` or `personal`.
```json
{
  "aws": ["production", "staging"]
}
```

### 🛠️ Disabling Guardrails for Local Tools
If you want to use Docker or npm without any interference from DeployShield:
```json
{
  "docker": [],
  "npm": []
}
```

## Security Defaults

- **Secure by Default**: If a provider is guarded but missing from your config, it is blocked.
- **Failed Detection**: If DeployShield cannot determine the context (e.g., missing kubeconfig), it assumes the context is sensitive and **blocks** the operation.

## Troubleshooting

### Config not loading?
- Verify the file is named exactly `.deployshield.json`.
- Ensure the JSON is valid (no trailing commas).
- Check the current working directory or `$HOME`.

### Command being blocked unexpectedly?
- Run the command with `echo $KUBECONFIG` or `echo $AWS_PROFILE` to see what context is active.
- Use `*` patterns in your config to see if a broader match fixes the issue.
- Remember that context detection prioritize CLI flags over environment variables.
