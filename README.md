# 🛡️ DeployShield

[![Tests](https://github.com/matanryngler/deployshield/actions/workflows/test.yml/badge.svg)](https://github.com/matanryngler/deployshield/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/matanryngler/deployshield)](https://github.com/matanryngler/deployshield/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Support](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)

**DeployShield** is a cross-platform production safety guardrail for **Claude Code** and **Gemini CLI**. It intercepts terminal commands before execution and blocks dangerous operations (writes, deletes, etc.) while allowing read-only commands to pass through.

## 🚀 Why DeployShield?

Large Language Models (LLMs) are incredibly capable but can accidentally execute destructive commands in production environments. DeployShield provides a **deterministic safety layer** that doesn't rely on probabilistic model instructions.

- **Deterministic Protection**: Uses a curated safe-list of read-only subcommands.
- **Recursive Safety**: Deeply scans subshells, backticks, `sudo`, and `bash -c`.
- **Context-Aware**: Granular control—block writes in `production` while allowing them in `dev`.
- **Zero-Dependency**: Fast, lightweight, and runs on any system with Python 3.8+.

---

## 🛠️ Supported Providers

| Category | Guarded CLIs |
| :--- | :--- |
| **☁️ Cloud** | `aws`, `gcloud`, `az`, `kubectl`, `helm` |
| **🗄️ Databases** | `psql`, `mysql`, `mongosh`, `redis-cli` |
| **🏗️ IaC** | `terraform`, `pulumi`, `cdk`, `sam`, `serverless` (`sls`), `ansible-playbook` |
| **📦 Publishing** | `npm`, `yarn`, `pnpm`, `cargo`, `twine`, `gem` |
| **🔧 Other** | `vault`, `gh`, `docker`, `podman` |

---

## 📥 Installation

### **Claude Code**
1. Register the marketplace:
   ```bash
   /plugin marketplace add matanryngler/deployshield
   ```
2. Install the plugin:
   ```bash
   /plugin install deployshield
   ```

### **Gemini CLI**
1. Install directly via GitHub:
   ```bash
   gemini extensions install https://github.com/matanryngler/deployshield
   ```

---

## ⚙️ Context-Aware Blocking

By default, DeployShield blocks ALL write operations. Create a `.deployshield.json` file to allow writes in non-production contexts.

**Example Config (`.deployshield.json`):**
```json
{
  "kubectl": ["prod-cluster", "production", "prod-*"],
  "aws": ["production-profile"],
  "terraform": ["prod-workspace"]
}
```
*Result: `kubectl apply` is allowed on your local `minikube` but blocked on `prod-cluster-01`.*

---

## 🛡️ Recursive Safety

DeployShield provides deep protection that handles common bypass attempts:
- **Nested Subshells**: `echo $(terraform destroy)` → **Blocked**
- **Administrative Wrappers**: `sudo kubectl delete ...` → **Blocked**
- **Shell Wrappers**: `bash -c "aws s3 rm ..."` → **Blocked**
- **Process Substitution**: `cat <(pulumi destroy)` → **Blocked**

---

## 🤝 Contributing

This project uses **`uv`** for dependency management and **`pre-commit`** for quality control.

```bash
# Run tests
uv run pytest -v

# Install pre-commit hooks
uv run pre-commit install
```

### License
MIT
