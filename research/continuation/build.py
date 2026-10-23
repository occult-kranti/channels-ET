#!/usr/bin/env python3
"""Rebuild retained analysis, manuscript and dashboard; never run a live crawl or LLM."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-expansion', action='store_true', help='Reuse the already built historical expansion')
    parser.add_argument('--skip-paper', action='store_true', help='Keep existing PDFs; do not certify a fresh paper build')
    options = parser.parse_args()
    env = os.environ.copy()
    env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env['PATH']
    env.setdefault('OPENBLAS_NUM_THREADS', '2')
    env.setdefault('OMP_NUM_THREADS', '2')
    env.setdefault('MPLCONFIGDIR', '/workspace/setup-validation/matplotlib')
    env.setdefault('XDG_CACHE_HOME', '/workspace/setup-validation/cache')

    def python(relative, *args):
        subprocess.run([sys.executable, str(HERE / relative), *args], cwd=ROOT, env=env, check=True)

    if not options.skip_expansion:
        args = ['--skip-paper'] if options.skip_paper else []
        python('../expansion/build.py', *args)
    python('models/verify_benchmark.py', '--offline')
    python('models/verify_round11.py')
    python('models/build_annotation_comparison.py')
    python('models/verify_round12.py')
    python('literature/verify_label_probes.py')
    python('acquisition/verify_pipeline.py')
    python('analysis/audit_benchmark.py')
    python('analysis/audit_model_diagnostics.py')
    python('analysis/audit_prompt_sensitivity.py')
    python('analysis/analyze.py')
    python('analysis/figures.py')
    python('analysis/verify.py')
    python('analysis/reproduce.py')
    if not options.skip_paper:
        subprocess.run(['bash', str(HERE / 'paper/build.sh')], cwd=ROOT, env=env, check=True)
    python('dashboard/build_dashboard.py')
    python('verify_release.py')
    print('PASS: retained-source rebuild. Neural inference, training, exact re-tokenization and live acquisition were not replayed.')


if __name__ == '__main__':
    main()
