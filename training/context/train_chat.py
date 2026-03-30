import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.config import load_yaml_config
from training.common.utils import ensure_dir


def main() -> int:
    parser = argparse.ArgumentParser(description='Chat-friendly context trainer runner.')
    parser.add_argument('--config', default='training/configs/context.yaml')
    parser.add_argument('--poll-seconds', type=float, default=2.0)
    args = parser.parse_args()

    config = load_yaml_config(args.config)
    metrics_dir = ensure_dir(config['output']['metrics_dir'])
    status_path = metrics_dir / 'live_status.json'
    progress_path = metrics_dir / 'live_progress.log'

    for path in (status_path, progress_path):
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    command = [
        sys.executable,
        '-u',
        str(ROOT / 'training' / 'context' / 'train.py'),
        '--config',
        args.config,
    ]
    print(f'Launching: {command}', flush=True)
    proc = subprocess.Popen(
        command,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    last_line_count = 0
    last_stage = None
    while True:
        if progress_path.exists():
            try:
                lines = progress_path.read_text(encoding='utf-8').splitlines()
            except Exception:
                lines = []
            if len(lines) > last_line_count:
                for line in lines[last_line_count:]:
                    print(line, flush=True)
                last_line_count = len(lines)

        if status_path.exists():
            try:
                status = json.loads(status_path.read_text(encoding='utf-8'))
                stage = status.get('stage')
                if stage != last_stage:
                    print(f'Current stage: {stage}', flush=True)
                    last_stage = stage
            except Exception:
                pass

        rc = proc.poll()
        if rc is not None:
            # Flush any remaining progress lines.
            if progress_path.exists():
                try:
                    lines = progress_path.read_text(encoding='utf-8').splitlines()
                except Exception:
                    lines = []
                if len(lines) > last_line_count:
                    for line in lines[last_line_count:]:
                        print(line, flush=True)
                    last_line_count = len(lines)
            print(f'Training process exited with code {rc}', flush=True)
            return rc

        time.sleep(args.poll_seconds)


if __name__ == '__main__':
    raise SystemExit(main())
