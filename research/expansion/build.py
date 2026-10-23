#!/usr/bin/env python3
"""Rebuild the expansion from retained sources without making network requests."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ATLAS = HERE.parents[1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-paper', action='store_true', help='Build data/explorer only; does not validate a new PDF')
    args = parser.parse_args()
    task_env = os.environ.copy()
    task_env.setdefault('MPLCONFIGDIR', '/workspace/setup-validation/matplotlib')
    task_env.setdefault('XDG_CACHE_HOME', '/workspace/setup-validation/cache')
    task_env.setdefault('OPENBLAS_NUM_THREADS', '2')
    task_env.setdefault('OMP_NUM_THREADS', '2')
    task_env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + task_env['PATH']
    scripts = ['qa/build_qa.py', 'qa/verify_qa.py',
               'analysis/analyze.py', 'analysis/figures.py', 'analysis/verify.py']
    for script in scripts:
        subprocess.run([sys.executable, str(HERE/script)], cwd=ATLAS, env=task_env, check=True)
    if not args.skip_paper:
        subprocess.run(['bash', str(HERE/'paper/build.sh')], cwd=ATLAS, env=task_env, check=True)
    for script in ('dashboard/build_dashboard.py', 'verify_release.py'):
        subprocess.run([sys.executable, str(HERE/script)], cwd=ATLAS, env=task_env, check=True)
