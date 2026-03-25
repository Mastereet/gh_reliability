#!/usr/bin/env bash
set -Eeuo pipefail

fct_execute_this() {
    readonly repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

    cd "${repo_root}"
    UV_CACHE_DIR=.uv-cache uv run python scripts/run_validation.py "$@"
}

fct_main() {
    fct_execute_this "$@"
}

fct_main "$@"
