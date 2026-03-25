# Design: Recursive Wrapper Normalization for DeployShield

**Date:** 2026-03-25
**Status:** Draft

## Problem Statement
DeployShield can be bypassed using "wrapper" commands that are not in the `PROVIDERS` list. 
Currently, the validator only checks the primary binary of a command segment. This means:
1. `sudo terraform apply` is **ALLOWED** (because `sudo` is not guarded).
2. `bash -c "kubectl delete pods --all"` is **ALLOWED** (because `bash` is not guarded).
3. `env AWS_PROFILE=prod terraform apply` is **ALLOWED** (because `env` is not guarded).

## Proposed Solution: Recursive Normalization
The `normalize_segment` and `check_segment` functions will be updated to recognize "wrappers" and recursively validate their contents.

### 1. `sudo` and `env` Normalization
- **Identify**: Check if the first token is `sudo` or `env`.
- **Unwrap**: Skip common flags (`-u`, `-E`, `-i`, `-n` for `sudo`; `-i`, `-u` for `env`) to find the next meaningful token.
- **Recurse**: Re-run the normalization and validation on the remaining tokens.

### 2. Shell String (`bash -c`, `sh -c`) Normalization
- **Identify**: Check if the first token is `bash` or `sh`.
- **Extract**: Find the `-c` flag and its associated command string argument.
- **Segment**: Use the existing `split_compound_command` on the extracted string.
- **Validate**: Call `check_segment` on each extracted segment.

### 3. Updated `check_segment` Flow
```python
def check_segment(segment: str) -> None:
    # A. Check nested subshells $(...) and `...` (Already implemented)
    nested = extract_nested_contents(segment)
    for ncmd in nested:
        for iseg in split_compound_command(ncmd):
            check_segment(iseg)

    # B. Normalize binary and unwrap sudo/env
    binary, args = normalize_segment(segment)
    if not binary: return

    # C. Handle shell wrappers bash -c / sh -c
    if binary in ("bash", "sh"):
        cmd_str = extract_flag_value(args, "-c")
        if cmd_str:
            for iseg in split_compound_command(cmd_str):
                check_segment(iseg)
            return # Shell itself is not guarded, only its contents

    # D. Standard provider check
    if binary in PROVIDERS:
        # Context-aware logic + safe-list check
        # ...
```

## Security & Reliability
- **Secure by Default**: If detection fails (e.g. malformed shell string), the validator falls back to blocking if a guarded CLI is detected later.
- **Infinite Recursion Protection**: Wrappers are consumed one level at a time. A loop like `sudo sudo ...` will naturally terminate when all tokens are processed.
- **Path Stripping**: Wrappers called with full paths (`/usr/bin/sudo`) are correctly normalized to their binary names.

## Testing Strategy
- **Unit Tests**:
    - `sudo aws s3 ls` (Allowed)
    - `sudo terraform apply` (Blocked)
    - `env VAR=val terraform apply` (Blocked)
    - `bash -c "kubectl apply -f ..."` (Blocked)
    - `sudo bash -c "terraform apply"` (Blocked)
- **Integration Tests**:
    - Full end-to-end piping tests for wrapped commands.
