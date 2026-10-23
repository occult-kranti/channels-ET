#!/usr/bin/env bash
# Recreate the two tested Python 3.12 CPU environments; keep weights outside Git.
set -euo pipefail
CHANNELS_ET_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
python3 -m venv /workspace/channels-et-model-venv
/workspace/channels-et-model-venv/bin/python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu 'torch==2.6.0+cpu'
/workspace/channels-et-model-venv/bin/python -m pip install --no-cache-dir -r "$CHANNELS_ET_PROJECT_ROOT/research/continuation/models/cpu-environment-freeze.txt"
/workspace/channels-et-model-venv/bin/python -m pip check
python3 -m venv /workspace/channels-et-modern-venv
# Share only CPU Torch and small dependencies, not baseline Transformers/PEFT.
python3 - <<'PY'
import pathlib
base=pathlib.Path('/workspace/channels-et-model-venv/lib/python3.12/site-packages')
dest=pathlib.Path('/workspace/channels-et-modern-venv/lib/python3.12/site-packages')
for pattern in ['torch','torchgen','functorch','torch-*.dist-info','sympy','sympy-*.dist-info',
                'mpmath','mpmath-*.dist-info','networkx','networkx-*.dist-info',
                'jinja2','jinja2-*.dist-info','markupsafe','markupsafe-*.dist-info']:
    for source in base.glob(pattern):
        target=dest/source.name
        if not target.exists(): target.symlink_to(source,target_is_directory=source.is_dir())
PY
/workspace/channels-et-modern-venv/bin/python -m pip install --no-cache-dir -r "$CHANNELS_ET_PROJECT_ROOT/research/continuation/models/modern-environment-freeze.txt"
/workspace/channels-et-modern-venv/bin/python -m pip check
/workspace/channels-et-modern-venv/bin/python - <<'PY'
import importlib.util, torch, transformers
assert torch.__version__=='2.6.0+cpu' and transformers.__version__=='5.20.2'
assert importlib.util.find_spec('peft') is None
print('Modern CPU environment verified; baseline PEFT is isolated.')
PY
