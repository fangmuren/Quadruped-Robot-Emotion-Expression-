import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

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

from promp_runtime import (
    DEFAULT_FINISH_STEP,
    DEFAULT_PREPARATION_STEPS,
    ModelTrajectoryRunner,
    build_deterministic_traj,
    summarize_traj,
    traj_to_steps,
    write_traj,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / 'data' / 'happy_promp' / 'models' / 'happy_mid_promp.npz'
MODEL_LOW_PATH = PROJECT_ROOT / 'data' / 'happy_promp' / 'models' / 'happy_low_promp.npz'
MODEL_HIGH_PATH = PROJECT_ROOT / 'data' / 'happy_promp' / 'models' / 'happy_high_promp.npz'


class FakeController:
    def __init__(self, fail_on_send_number=None):
        self.commands = []
        self.closed = False
        self._fail_on_send_number = fail_on_send_number
        self._send_count = 0

    def send_command(self, **kwargs):
        self._send_count += 1
        if self._fail_on_send_number is not None and self._send_count == self._fail_on_send_number:
            raise RuntimeError('boom')
        self.commands.append(kwargs.copy())

    def close(self):
        self.closed = True


def failing_controller_factory():
    raise AssertionError('controller should not be created')


def make_two_frame_runner_traj():
    return {
        'dt_ms': 50,
        'n_frames': 2,
        'phase': [0.0, 1.0],
        'time_ms': [0, 50],
        'channels': {
            'velocity_x': [0.05, 0.06],
            'yaw_rate': [0.0, 0.1],
            'step_height_front': [0.02, 0.03],
            'step_height_hind': [0.02, 0.03],
            'body_height': [0.24, 0.25],
            'pitch': [0.02, 0.08],
        },
    }


class PrompRuntimeDeterministicTrajTest(unittest.TestCase):
    def test_build_deterministic_traj_reconstructs_expected_shape(self):
        traj = build_deterministic_traj(MODEL_PATH)

        self.assertEqual(traj['sample_id'], 'happy_promp_runtime')
        self.assertEqual(traj['emotion'], 'happy')
        self.assertEqual(traj['intensity'], 'mid')
        self.assertEqual(traj['dt_ms'], 50)
        self.assertEqual(traj['n_frames'], 45)
        self.assertEqual(len(traj['phase']), 45)
        self.assertEqual(len(traj['time_ms']), 45)
        self.assertEqual(traj['time_ms'][0], 0)
        self.assertEqual(traj['time_ms'][-1], 2200)
        self.assertEqual(sorted(traj['channels'].keys()), [
            'body_height',
            'pitch',
            'step_height_front',
            'step_height_hind',
            'velocity_x',
            'yaw_rate',
        ])
        self.assertEqual(traj['aux_labels']['ornament_type'], 'promp_sample')
        self.assertTrue(traj['aux_labels']['returns_to_neutral'])
        self.assertEqual(traj['meta']['source'], 'promp_sample')

    def test_summarize_traj_reports_duration_and_channel_ranges(self):
        traj = build_deterministic_traj(MODEL_PATH)

        summary = summarize_traj(traj)

        self.assertEqual(summary['n_frames'], 45)
        self.assertEqual(summary['dt_ms'], 50)
        self.assertEqual(summary['total_duration_ms'], 2200)
        self.assertIn('velocity_x', summary['channel_ranges'])
        self.assertIn('pitch', summary['channel_ranges'])
        self.assertLessEqual(
            summary['channel_ranges']['velocity_x']['min'],
            summary['channel_ranges']['velocity_x']['max'],
        )

    def test_build_deterministic_traj_infers_low_and_high_intensity_from_model_filename(self):
        low_traj = build_deterministic_traj(MODEL_LOW_PATH)
        high_traj = build_deterministic_traj(MODEL_HIGH_PATH)

        self.assertEqual(low_traj['emotion'], 'happy')
        self.assertEqual(low_traj['intensity'], 'low')
        self.assertEqual(high_traj['emotion'], 'happy')
        self.assertEqual(high_traj['intensity'], 'high')


class PrompRuntimeAdapterTest(unittest.TestCase):
    def test_traj_to_steps_maps_velocity_x_and_clamps_runtime_channels(self):
        traj = {
            'dt_ms': 50,
            'n_frames': 2,
            'phase': [0.0, 1.0],
            'time_ms': [0, 50],
            'channels': {
                'velocity_x': [0.03, 0.088889],
                'yaw_rate': [-0.3, 0.3],
                'step_height_front': [-0.01, 0.06],
                'step_height_hind': [0.07, -0.02],
                'body_height': [0.2, 0.3],
                'pitch': [-0.1, 0.3],
            },
        }

        steps = traj_to_steps(traj)

        self.assertEqual(steps, [
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [0.2, 0.0, -0.25],
                'step_height': [0.0, 0.05],
                'body_height': 0.22,
                'rpy': [0.0, -0.05, 0.0],
                'duration': 50,
            },
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [0.4, 0.0, 0.25],
                'step_height': [0.05, 0.0],
                'body_height': 0.27,
                'rpy': [0.0, 0.2, 0.0],
                'duration': 50,
            },
        ])

    def test_traj_to_steps_maps_deterministic_velocity_x_into_robot_command_range(self):
        traj = build_deterministic_traj(MODEL_LOW_PATH)

        steps = traj_to_steps(traj)
        source_velocity_x = traj['channels']['velocity_x']
        mapped_velocity_x = [step['velocity'][0] for step in steps]

        self.assertTrue(steps)
        self.assertEqual(len(mapped_velocity_x), len(source_velocity_x))
        self.assertGreater(max(source_velocity_x) - min(source_velocity_x), 0.0)
        self.assertGreater(max(mapped_velocity_x) - min(mapped_velocity_x), 0.0)
        source_min, source_max = 0.03, 0.088889
        target_min, target_max = 0.2, 0.4
        for source_value, mapped_value in zip(source_velocity_x, mapped_velocity_x):
            normalized = (source_value - source_min) / (source_max - source_min)
            expected_value = target_min + normalized * (target_max - target_min)
            expected_value = max(target_min, min(expected_value, target_max))
            self.assertAlmostEqual(mapped_value, expected_value)
        self.assertGreater(len(set(mapped_velocity_x)), 1)


class PrompRuntimePersistenceTest(unittest.TestCase):
    def test_write_traj_saves_deterministic_output(self):
        traj = build_deterministic_traj(MODEL_PATH)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'runtime.traj.json'
            write_traj(output_path, traj)

            self.assertTrue(output_path.exists())
            saved = json.loads(output_path.read_text(encoding='utf-8'))
            self.assertEqual(saved['sample_id'], traj['sample_id'])
            self.assertEqual(saved['emotion'], traj['emotion'])
            self.assertEqual(saved['channels']['velocity_x'], traj['channels']['velocity_x'])


class PrompRuntimeRunnerTest(unittest.TestCase):
    def test_runner_dry_run_skips_controller_and_returns_steps(self):
        runner = ModelTrajectoryRunner(controller_factory=failing_controller_factory)
        traj = build_deterministic_traj(MODEL_PATH)

        result = runner.run_traj(traj, dry_run=True)

        self.assertEqual(result['status'], 'dry_run')
        self.assertEqual(result['summary']['n_frames'], 45)
        self.assertEqual(len(result['steps']), 45)

    def test_runner_sends_preparation_then_frames_then_finish(self):
        controller = FakeController()
        traj = make_two_frame_runner_traj()
        runner = ModelTrajectoryRunner(controller_factory=lambda: controller)

        result = runner.run_traj(traj)

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(controller.commands[:2], DEFAULT_PREPARATION_STEPS)
        self.assertEqual(controller.commands[2]['velocity'], traj_to_steps(traj)[0]['velocity'])
        self.assertEqual(controller.commands[3]['rpy'], [0.0, 0.08, 0.0])
        self.assertEqual(controller.commands[-1], DEFAULT_FINISH_STEP)
        self.assertEqual(len(controller.commands), 5)
        self.assertTrue(controller.closed)

    def test_runner_paces_frames_and_emits_coarse_logs(self):
        controller = FakeController()
        traj = make_two_frame_runner_traj()
        sleeps = []
        logs = []
        runner = ModelTrajectoryRunner(
            controller_factory=lambda: controller,
            sleep_fn=sleeps.append,
            log_fn=logs.append,
        )

        result = runner.run_traj(traj)

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(sleeps, [0.05, 0.05])
        self.assertIn('controller_start', logs)
        self.assertIn('preparation_start', logs)
        self.assertIn('playback_start n_frames=2 dt_ms=50', logs)
        self.assertIn('playback_frame=1/2', logs)
        self.assertIn('playback_frame=2/2', logs)
        self.assertIn('finish_start', logs)
        self.assertEqual(
            logs,
            [
                'controller_start',
                'preparation_start',
                'playback_start n_frames=2 dt_ms=50',
                'playback_frame=1/2',
                'playback_frame=2/2',
                'finish_start',
                'controller_shutdown',
            ],
        )

    def test_runner_attempts_finish_once_after_send_failure(self):
        first_frame_send_number = len(DEFAULT_PREPARATION_STEPS) + 2
        controller = FakeController(fail_on_send_number=first_frame_send_number)
        traj = make_two_frame_runner_traj()
        runner = ModelTrajectoryRunner(controller_factory=lambda: controller)
        expected_steps = traj_to_steps(traj)

        with self.assertRaises(RuntimeError) as exc_info:
            runner.run_traj(traj)

        self.assertEqual(controller.commands[:len(DEFAULT_PREPARATION_STEPS)], DEFAULT_PREPARATION_STEPS)
        self.assertIn(expected_steps[0], controller.commands)
        self.assertNotIn(expected_steps[1], controller.commands)
        self.assertEqual(controller.commands.count(DEFAULT_FINISH_STEP), 1)
        self.assertEqual(
            len(controller.commands),
            len(DEFAULT_PREPARATION_STEPS) + 1 + 1,
        )
        self.assertTrue(controller.closed)
        self.assertEqual(str(exc_info.exception), 'boom')


if __name__ == '__main__':
    unittest.main()
