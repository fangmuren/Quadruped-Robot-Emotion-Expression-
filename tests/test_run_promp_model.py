import io
import sys
import time
import types
import unittest
from pathlib import Path
from unittest import mock

import bootstrap  # noqa: F401


class FakeLCMModule:
    class LCM:
        def __init__(self, *args, **kwargs):
            self.published = []

        def subscribe(self, *args, **kwargs):
            return object()

        def unsubscribe(self, *args, **kwargs):
            pass

        def handle(self):
            time.sleep(0.001)

        def handle_timeout(self, timeout_ms):
            time.sleep(min(timeout_ms / 1000.0, 0.001))

        def publish(self, *args, **kwargs):
            self.published.append(args)


sys.modules.setdefault('lcm', types.SimpleNamespace(LCM=FakeLCMModule.LCM))

import run_promp_model


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / 'data' / 'happy_promp' / 'models' / 'happy_mid_promp.npz'


class RunPrompModelCliTest(unittest.TestCase):
    def test_main_passes_flags_to_runner_and_prints_summary(self):
        fake_result = {
            'status': 'dry_run',
            'summary': {
                'n_frames': 45,
                'dt_ms': 50,
                'total_duration_ms': 2200,
                'channel_ranges': {
                    'velocity_x': {'min': 0.03, 'max': 0.07},
                    'pitch': {'min': 0.0, 'max': 0.1},
                },
            },
        }
        fake_runner = mock.Mock()
        fake_runner.run_model.return_value = fake_result

        stdout = io.StringIO()
        with mock.patch('run_promp_model.ModelTrajectoryRunner', return_value=fake_runner):
            exit_code = run_promp_model.main([
                str(MODEL_PATH),
                '--dry-run',
                '--print-summary',
                '--save-traj',
                'tmp/output.traj.json',
            ], stdout=stdout)

        self.assertEqual(exit_code, 0)
        fake_runner.run_model.assert_called_once_with(
            MODEL_PATH,
            dry_run=True,
            save_traj_path=Path('tmp/output.traj.json'),
        )
        output = stdout.getvalue()
        self.assertIn('status=dry_run', output)
        self.assertIn('n_frames=45', output)
        self.assertIn('velocity_x', output)

    def test_main_passes_dry_run_without_robot_controller_dependency(self):
        fake_result = {
            'status': 'dry_run',
            'summary': {
                'n_frames': 45,
                'dt_ms': 50,
                'total_duration_ms': 2200,
                'channel_ranges': {
                    'velocity_x': {'min': 0.03, 'max': 0.07},
                },
            },
        }
        stdout = io.StringIO()

        with mock.patch('run_promp_model.ModelTrajectoryRunner') as runner_cls:
            runner_cls.return_value.run_model.return_value = fake_result
            exit_code = run_promp_model.main([
                str(MODEL_PATH),
                '--dry-run',
                '--print-summary',
            ], stdout=stdout)

        self.assertEqual(exit_code, 0)
        self.assertIn('status=dry_run', stdout.getvalue())

    def test_main_returns_non_zero_when_runner_raises_runtime_error(self):
        fake_runner = mock.Mock()
        fake_runner.run_model.side_effect = RuntimeError('boom')
        stdout = io.StringIO()

        with mock.patch('run_promp_model.ModelTrajectoryRunner', return_value=fake_runner):
            exit_code = run_promp_model.main([str(MODEL_PATH)], stdout=stdout)

        self.assertEqual(exit_code, 1)
        self.assertIn('boom', stdout.getvalue())

    def test_main_returns_interrupt_exit_code_on_keyboard_interrupt(self):
        fake_runner = mock.Mock()
        fake_runner.run_model.side_effect = KeyboardInterrupt()
        stdout = io.StringIO()

        with mock.patch('run_promp_model.ModelTrajectoryRunner', return_value=fake_runner):
            exit_code = run_promp_model.main([str(MODEL_PATH)], stdout=stdout)

        self.assertEqual(exit_code, 130)
        self.assertIn('interrupted', stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
