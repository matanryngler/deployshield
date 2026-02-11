# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-11

### Added
- `from __future__ import annotations` for Python 3.8+ compatibility
- `.gitignore` for Python artifacts
- `SECURITY.md` with vulnerability reporting guidelines
- `CHANGELOG.md` (this file)
- Comprehensive test suite (~100 tests via pytest)
- CI/CD with GitHub Actions (tests on Python 3.9/3.11/3.12 + ruff linting)
- Plugin metadata: `author`, `repository`, `homepage`, `license` fields in `plugin.json`
- `/deployshield-status` slash command for quick reference

### Fixed
- `.claude/settings.local.json` referenced `.sh` instead of `.py` for the validation script

## [1.0.0] - 2026-02-10

### Added
- Initial release with 27 guarded CLIs across 6 categories
- Quote-aware shell command parser supporting `&&`, `||`, `;`, `|`, subshells, backticks, and escapes
- Cloud providers: AWS, GCP, Azure, Kubernetes, Helm
- Database CLIs: psql, mysql, mongosh, redis-cli with SQL-aware checking
- IaC tools: Terraform, Pulumi, CDK, SAM, Serverless Framework, Ansible
- Secrets management: HashiCorp Vault
- GitHub CLI: gh (read-only API calls, safe subcommands)
- Container runtimes: Docker, Podman
- Package publishing guards: npm/yarn/pnpm, twine, gem, cargo
- Default-deny model for all guarded CLIs
- Dry-run detection for kubectl and helm
- Env-var prefix stripping and full binary path normalization
- PreToolUse hook integration with Claude Code plugin system
- SKILL.md for context-aware Claude guidance on infrastructure files

[1.1.0]: https://github.com/matanryngler/deployshield/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/matanryngler/deployshield/releases/tag/v1.0.0
