#!/usr/bin/env bash
# Records GPU, CUDA and exact package versions to versions.txt.
set -euo pipefail
out="${1:-versions.txt}"
{
  echo "# Recorded $(date -Iseconds)"
  echo "## nvidia-smi"
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
  echo "## python"
  python --version
  echo "## key packages"
  python - <<'PY'
import importlib.metadata as md
for pkg in ["unsloth", "unsloth_zoo", "trl", "vllm", "peft", "transformers", "datasets", "torch", "accelerate", "bitsandbytes"]:
    try:
        print(f"{pkg}=={md.version(pkg)}")
    except md.PackageNotFoundError:
        print(f"{pkg}: not installed")
PY
  echo "## pip freeze"
  uv pip freeze 2>/dev/null || pip freeze
} > "$out"
echo "Wrote $out"
