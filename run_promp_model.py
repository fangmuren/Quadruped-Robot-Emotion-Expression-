import argparse
import sys
from pathlib import Path

from promp_runtime import ModelTrajectoryRunner


def _build_parser():
    parser = argparse.ArgumentParser(
        description='Execute a deterministic happy ProMP model on the robot',
    )
    parser.add_argument('model_npz', type=Path, help='Path to happy ProMP model npz')
    parser.add_argument('--dry-run', action='store_true', help='Build traj and steps without connecting to the robot')
    parser.add_argument('--print-summary', action='store_true', help='Print deterministic traj summary after reconstruction')
    parser.add_argument('--save-traj', type=Path, default=None, help='Optional path to save deterministic traj json')
    return parser


def _write_summary(stdout, result):
    summary = result['summary']
    stdout.write(f"status={result['status']}\n")
    stdout.write(f"n_frames={summary['n_frames']}\n")
    stdout.write(f"dt_ms={summary['dt_ms']}\n")
    stdout.write(f"total_duration_ms={summary['total_duration_ms']}\n")
    for channel_name in sorted(summary['channel_ranges']):
        channel_range = summary['channel_ranges'][channel_name]
        stdout.write(
            f"{channel_name}: min={channel_range['min']}, max={channel_range['max']}\n"
        )


def main(argv=None, stdout=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    stream = stdout or sys.stdout
    runner = ModelTrajectoryRunner()

    try:
        result = runner.run_model(
            args.model_npz,
            dry_run=args.dry_run,
            save_traj_path=args.save_traj,
        )
    except KeyboardInterrupt:
        stream.write('interrupted\n')
        return 130
    except Exception as exc:
        stream.write(f'{exc}\n')
        return 1

    if args.print_summary:
        _write_summary(stream, result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
