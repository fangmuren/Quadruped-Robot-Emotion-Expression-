# Traj-to-Robot Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone CLI that accepts a happy ProMP `model.npz`, reconstructs a deterministic trajectory from `mu_w`, adapts each frame into existing robot runtime step commands, and plays them with fixed preparation and finish motions.

**Architecture:** Keep the current `main.py` / `motion_sequence.py` emotion path untouched. Add a focused `promp_runtime.py` module that owns deterministic trajectory reconstruction, traj-to-step adaptation, and the standalone runner lifecycle, then add `run_promp_model.py` as a thin CLI wrapper around that module.

**Tech Stack:** Python 3, stdlib `argparse`, `time`, `json`, `pathlib`, existing `data.happy_promp.sample_happy_promp` helpers, existing `CyberDogController`, stdlib `unittest`, `pytest`

---

### File Structure

- `promp_runtime.py` — deterministic model loading, in-memory traj construction, traj summary helpers, traj-to-step adaptation, fixed preparation/finish motions, standalone runner orchestration.
- `run_promp_model.py` — CLI argument parsing and exit-code handling for the standalone runtime.
- `tests/test_promp_runtime.py` — deterministic reconstruction, adapter mapping, dry-run behavior, and runner orchestration tests.
- `tests/test_run_promp_model.py` — CLI flag parsing, delegated execution, and error-path tests.

### Task 1: Lock the deterministic runtime contract in tests

**Files:**
- Create: `tests/test_promp_runtime.py`
- Test: `tests/test_promp_runtime.py`

- [ ] **Step 1: Create the failing runtime test file**

Write `tests/test_promp_runtime.py` with this content:

```python
import tempfile
import unittest
from pathlib import Path

import bootstrap  # noqa: F401

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


class FakeController:
    def __init__(self, fail_on_send_number=None):
        self.commands = []
        self.closed = False
        self._fail_on_send_number = fail_on_send_number

    def send_command(self, **kwargs):
        next_index = len(self.commands) + 1
        if self._fail_on_send_number is not None and next_index == self._fail_on_send_number:
            raise RuntimeError('boom')
        self.commands.append(kwargs.copy())

    def close(self):
        self.closed = True


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


class PrompRuntimeAdapterTest(unittest.TestCase):
    def test_traj_to_steps_maps_channels_into_happy_runtime_defaults(self):
        traj = {
            'dt_ms': 50,
            'n_frames': 2,
            'phase': [0.0, 1.0],
            'time_ms': [0, 50],
            'channels': {
                'velocity_x': [0.05, 0.06],
                'yaw_rate': [-0.1, 0.1],
                'step_height_front': [0.02, 0.03],
                'step_height_hind': [0.021, 0.031],
                'body_height': [0.24, 0.25],
                'pitch': [0.02, 0.08],
            },
        }

        steps = traj_to_steps(traj)

        self.assertEqual(steps, [
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [0.05, 0.0, -0.1],
                'step_height': [0.02, 0.021],
                'body_height': 0.24,
                'rpy': [0.0, 0.02, 0.0],
                'duration': 50,
            },
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [0.06, 0.0, 0.1],
                'step_height': [0.03, 0.031],
                'body_height': 0.25,
                'rpy': [0.0, 0.08, 0.0],
                'duration': 50,
            },
        ])


class PrompRuntimePersistenceTest(unittest.TestCase):
    def test_write_traj_saves_deterministic_output(self):
        traj = build_deterministic_traj(MODEL_PATH)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'runtime.traj.json'
            write_traj(output_path, traj)
            self.assertTrue(output_path.exists())
            self.assertIn('velocity_x', output_path.read_text(encoding='utf-8'))


class PrompRuntimeRunnerTest(unittest.TestCase):
    def test_runner_dry_run_skips_controller_and_returns_steps(self):
        runner = ModelTrajectoryRunner(controller_factory=lambda: (_ for _ in ()).throw(AssertionError('controller should not be created')))
        traj = build_deterministic_traj(MODEL_PATH)

        result = runner.run_traj(traj, dry_run=True)

        self.assertEqual(result['status'], 'dry_run')
        self.assertEqual(result['summary']['n_frames'], 45)
        self.assertEqual(len(result['steps']), 45)

    def test_runner_sends_preparation_then_frames_then_finish(self):
        controller = FakeController()
        traj = {
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
        runner = ModelTrajectoryRunner(controller_factory=lambda: controller)

        result = runner.run_traj(traj)

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(controller.commands[0], DEFAULT_PREPARATION_STEPS[0])
        self.assertEqual(controller.commands[1], DEFAULT_PREPARATION_STEPS[1])
        self.assertEqual(controller.commands[2]['velocity'], [0.05, 0.0, 0.0])
        self.assertEqual(controller.commands[3]['rpy'], [0.0, 0.08, 0.0])
        self.assertEqual(controller.commands[4], DEFAULT_FINISH_STEP)
        self.assertTrue(controller.closed)

    def test_runner_attempts_finish_once_after_send_failure(self):
        controller = FakeController(fail_on_send_number=4)
        traj = {
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
        runner = ModelTrajectoryRunner(controller_factory=lambda: controller)

        with self.assertRaises(RuntimeError):
            runner.run_traj(traj)

        self.assertEqual(controller.commands[0], DEFAULT_PREPARATION_STEPS[0])
        self.assertEqual(controller.commands[1], DEFAULT_PREPARATION_STEPS[1])
        self.assertEqual(controller.commands[2]['velocity'], [0.05, 0.0, 0.0])
        self.assertEqual(controller.commands[3], DEFAULT_FINISH_STEP)
        self.assertTrue(controller.closed)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the new runtime test file to verify it fails before implementation**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_promp_runtime.py"
```

Expected: FAIL with `ModuleNotFoundError: No module named 'promp_runtime'`.

- [ ] **Step 3: Commit the red runtime tests**

```bash
git add tests/test_promp_runtime.py
git commit -m "test: define traj runtime contract"
```

### Task 2: Implement deterministic traj reconstruction and traj-to-step adaptation

**Files:**
- Create: `promp_runtime.py`
- Test: `tests/test_promp_runtime.py`

- [ ] **Step 1: Create `promp_runtime.py` with deterministic reconstruction, summary, persistence, and adapter helpers**

Write `promp_runtime.py` with this content:

```python
import json
from pathlib import Path

from data.happy_promp.sample_happy_promp import load_model, reconstruct_trajectory


DEFAULT_SAMPLE_ID = 'happy_promp_runtime'
DEFAULT_EMOTION = 'happy'
DEFAULT_INTENSITY = 'mid'
DEFAULT_MODE = 11
DEFAULT_GAIT_ID = 27
DEFAULT_VELOCITY_Y = 0.0
DEFAULT_RPY_ROLL = 0.0
DEFAULT_RPY_YAW = 0.0
DEFAULT_PREPARATION_STEPS = [
    {'mode': 12, 'gait_id': 0, 'duration': 6000},
    {'mode': 21, 'gait_id': 5, 'body_height': 0.24, 'duration': 400},
]
DEFAULT_FINISH_STEP = {'mode': 3, 'gait_id': 0, 'body_height': 0.23, 'duration': 600}
REQUIRED_CHANNELS = [
    'velocity_x',
    'yaw_rate',
    'step_height_front',
    'step_height_hind',
    'body_height',
    'pitch',
]


def build_deterministic_traj(model_path, sample_id=DEFAULT_SAMPLE_ID, emotion=DEFAULT_EMOTION, intensity=DEFAULT_INTENSITY):
    model = load_model(Path(model_path))
    channel_map = reconstruct_trajectory(model, model['mu_w'])
    phase = [round(float(value), 6) for value in model['phase']]
    time_ms = [model['dt_ms'] * idx for idx in range(model['n_frames'])]

    return {
        'sample_id': sample_id,
        'emotion': emotion,
        'intensity': intensity,
        'dt_ms': model['dt_ms'],
        'n_frames': model['n_frames'],
        'phase': phase,
        'time_ms': time_ms,
        'channels': channel_map,
        'aux_labels': {
            'ornament_type': 'promp_sample',
            'returns_to_neutral': True,
        },
        'meta': {
            'source': 'promp_sample',
            'model_n_basis': model['n_basis'],
        },
    }


def summarize_traj(traj):
    channels = traj['channels']
    total_duration_ms = traj['dt_ms'] * max(traj['n_frames'] - 1, 0)
    return {
        'n_frames': traj['n_frames'],
        'dt_ms': traj['dt_ms'],
        'total_duration_ms': total_duration_ms,
        'channel_ranges': {
            name: {
                'min': min(values),
                'max': max(values),
            }
            for name, values in channels.items()
        },
    }


def write_traj(path, traj):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as handle:
        json.dump(traj, handle, ensure_ascii=False, indent=2)


def _validate_traj(traj):
    for key in ('dt_ms', 'n_frames', 'phase', 'time_ms', 'channels'):
        if key not in traj:
            raise ValueError(f'missing traj field: {key}')

    channels = traj['channels']
    for channel in REQUIRED_CHANNELS:
        if channel not in channels:
            raise ValueError(f'missing channel: {channel}')
        if len(channels[channel]) != traj['n_frames']:
            raise ValueError(f'channel length mismatch for {channel}')


def traj_to_steps(traj):
    _validate_traj(traj)
    steps = []
    channels = traj['channels']
    for index in range(traj['n_frames']):
        steps.append({
            'mode': DEFAULT_MODE,
            'gait_id': DEFAULT_GAIT_ID,
            'velocity': [
                channels['velocity_x'][index],
                DEFAULT_VELOCITY_Y,
                channels['yaw_rate'][index],
            ],
            'step_height': [
                channels['step_height_front'][index],
                channels['step_height_hind'][index],
            ],
            'body_height': channels['body_height'][index],
            'rpy': [
                DEFAULT_RPY_ROLL,
                channels['pitch'][index],
                DEFAULT_RPY_YAW,
            ],
            'duration': traj['dt_ms'],
        })
    return steps
```

- [ ] **Step 2: Run the runtime tests and verify the helper contract passes while runner tests still fail**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_promp_runtime.py"
```

Expected: FAIL with `ImportError` or `AttributeError` mentioning `ModelTrajectoryRunner`, while the deterministic traj and adapter tests begin importing successfully.

- [ ] **Step 3: Commit the deterministic runtime helpers**

```bash
git add promp_runtime.py tests/test_promp_runtime.py
git commit -m "feat: add deterministic traj runtime helpers"
```

### Task 3: Implement the standalone runner lifecycle

**Files:**
- Modify: `promp_runtime.py`
- Test: `tests/test_promp_runtime.py`

- [ ] **Step 1: Extend `promp_runtime.py` with the runner class and high-level execution helper**

Replace `promp_runtime.py` with this content:

```python
import json
from pathlib import Path

from data.happy_promp.sample_happy_promp import load_model, reconstruct_trajectory
from robot_control import CyberDogController


DEFAULT_SAMPLE_ID = 'happy_promp_runtime'
DEFAULT_EMOTION = 'happy'
DEFAULT_INTENSITY = 'mid'
DEFAULT_MODE = 11
DEFAULT_GAIT_ID = 27
DEFAULT_VELOCITY_Y = 0.0
DEFAULT_RPY_ROLL = 0.0
DEFAULT_RPY_YAW = 0.0
DEFAULT_PREPARATION_STEPS = [
    {'mode': 12, 'gait_id': 0, 'duration': 6000},
    {'mode': 21, 'gait_id': 5, 'body_height': 0.24, 'duration': 400},
]
DEFAULT_FINISH_STEP = {'mode': 3, 'gait_id': 0, 'body_height': 0.23, 'duration': 600}
REQUIRED_CHANNELS = [
    'velocity_x',
    'yaw_rate',
    'step_height_front',
    'step_height_hind',
    'body_height',
    'pitch',
]


def build_deterministic_traj(model_path, sample_id=DEFAULT_SAMPLE_ID, emotion=DEFAULT_EMOTION, intensity=DEFAULT_INTENSITY):
    model = load_model(Path(model_path))
    channel_map = reconstruct_trajectory(model, model['mu_w'])
    phase = [round(float(value), 6) for value in model['phase']]
    time_ms = [model['dt_ms'] * idx for idx in range(model['n_frames'])]

    return {
        'sample_id': sample_id,
        'emotion': emotion,
        'intensity': intensity,
        'dt_ms': model['dt_ms'],
        'n_frames': model['n_frames'],
        'phase': phase,
        'time_ms': time_ms,
        'channels': channel_map,
        'aux_labels': {
            'ornament_type': 'promp_sample',
            'returns_to_neutral': True,
        },
        'meta': {
            'source': 'promp_sample',
            'model_n_basis': model['n_basis'],
        },
    }


def summarize_traj(traj):
    channels = traj['channels']
    total_duration_ms = traj['dt_ms'] * max(traj['n_frames'] - 1, 0)
    return {
        'n_frames': traj['n_frames'],
        'dt_ms': traj['dt_ms'],
        'total_duration_ms': total_duration_ms,
        'channel_ranges': {
            name: {
                'min': min(values),
                'max': max(values),
            }
            for name, values in channels.items()
        },
    }


def write_traj(path, traj):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as handle:
        json.dump(traj, handle, ensure_ascii=False, indent=2)


def _validate_traj(traj):
    for key in ('dt_ms', 'n_frames', 'phase', 'time_ms', 'channels'):
        if key not in traj:
            raise ValueError(f'missing traj field: {key}')

    channels = traj['channels']
    for channel in REQUIRED_CHANNELS:
        if channel not in channels:
            raise ValueError(f'missing channel: {channel}')
        if len(channels[channel]) != traj['n_frames']:
            raise ValueError(f'channel length mismatch for {channel}')


def traj_to_steps(traj):
    _validate_traj(traj)
    steps = []
    channels = traj['channels']
    for index in range(traj['n_frames']):
        steps.append({
            'mode': DEFAULT_MODE,
            'gait_id': DEFAULT_GAIT_ID,
            'velocity': [
                channels['velocity_x'][index],
                DEFAULT_VELOCITY_Y,
                channels['yaw_rate'][index],
            ],
            'step_height': [
                channels['step_height_front'][index],
                channels['step_height_hind'][index],
            ],
            'body_height': channels['body_height'][index],
            'rpy': [
                DEFAULT_RPY_ROLL,
                channels['pitch'][index],
                DEFAULT_RPY_YAW,
            ],
            'duration': traj['dt_ms'],
        })
    return steps


class ModelTrajectoryRunner:
    def __init__(self, controller_factory=CyberDogController):
        self.controller_factory = controller_factory

    def run_model(self, model_path, dry_run=False, save_traj_path=None):
        traj = build_deterministic_traj(model_path)
        if save_traj_path is not None:
            write_traj(save_traj_path, traj)
        return self.run_traj(traj, dry_run=dry_run)

    def run_traj(self, traj, dry_run=False):
        steps = traj_to_steps(traj)
        summary = summarize_traj(traj)

        if dry_run:
            return {
                'status': 'dry_run',
                'traj': traj,
                'steps': steps,
                'summary': summary,
            }

        controller = self.controller_factory()
        finish_sent = False
        try:
            for step in DEFAULT_PREPARATION_STEPS:
                controller.send_command(**step)
            for step in steps:
                controller.send_command(**step)
            controller.send_command(**DEFAULT_FINISH_STEP)
            finish_sent = True
            return {
                'status': 'completed',
                'traj': traj,
                'steps': steps,
                'summary': summary,
            }
        except KeyboardInterrupt:
            if not finish_sent:
                try:
                    controller.send_command(**DEFAULT_FINISH_STEP)
                except Exception:
                    pass
            raise
        except Exception:
            if not finish_sent:
                controller.send_command(**DEFAULT_FINISH_STEP)
            raise
        finally:
            controller.close()
```

- [ ] **Step 2: Run the runtime tests and verify they all pass**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_promp_runtime.py"
```

Expected: PASS with 6 passed.

- [ ] **Step 3: Commit the runner implementation**

```bash
git add promp_runtime.py tests/test_promp_runtime.py
git commit -m "feat: add standalone model trajectory runner"
```

### Task 4: Lock the CLI contract in tests

**Files:**
- Create: `tests/test_run_promp_model.py`
- Test: `tests/test_run_promp_model.py`

- [ ] **Step 1: Create the failing CLI test file**

Write `tests/test_run_promp_model.py` with this content:

```python
import io
import unittest
from pathlib import Path
from unittest import mock

import bootstrap  # noqa: F401

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
```

- [ ] **Step 2: Run the CLI tests to verify they fail before implementation**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_run_promp_model.py"
```

Expected: FAIL with `ModuleNotFoundError: No module named 'run_promp_model'`.

- [ ] **Step 3: Commit the red CLI tests**

```bash
git add tests/test_run_promp_model.py
git commit -m "test: define model runtime cli contract"
```

### Task 5: Implement the standalone CLI entrypoint

**Files:**
- Create: `run_promp_model.py`
- Test: `tests/test_run_promp_model.py`

- [ ] **Step 1: Create `run_promp_model.py` with the standalone CLI and summary output**

Write `run_promp_model.py` with this content:

```python
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
```

- [ ] **Step 2: Run the CLI tests and verify they pass**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_run_promp_model.py"
```

Expected: PASS with 3 passed.

- [ ] **Step 3: Commit the CLI implementation**

```bash
git add run_promp_model.py tests/test_run_promp_model.py
git commit -m "feat: add promp model cli entrypoint"
```

### Task 6: Run focused regressions and one dry-run smoke command

**Files:**
- Verify: `tests/test_promp_runtime.py`
- Verify: `tests/test_run_promp_model.py`
- Verify: `data/happy_promp/models/happy_mid_promp.npz`

- [ ] **Step 1: Run the focused regression suite**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_promp_runtime.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_run_promp_model.py"
```

Expected: PASS with 9 passed.

- [ ] **Step 2: Run a dry-run smoke command against the checked-in happy model**

Run:
```bash
python3 "/home/grazier/cyberdog_ws/Emotion_dog/run_promp_model.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/data/happy_promp/models/happy_mid_promp.npz" \
  --dry-run --print-summary --save-traj \
  "/tmp/happy_mid_runtime.traj.json"
```

Expected output contains:
- `status=dry_run`
- `n_frames=45`
- `dt_ms=50`
- `total_duration_ms=2200`
- `velocity_x:`

Expected filesystem result:
- `/tmp/happy_mid_runtime.traj.json` exists and contains `"sample_id": "happy_promp_runtime"`

- [ ] **Step 3: Commit the verified runtime**

```bash
git add promp_runtime.py run_promp_model.py tests/test_promp_runtime.py tests/test_run_promp_model.py
git commit -m "feat: execute deterministic promp trajectories"
```

## Self-Review

### Spec coverage

- deterministic `model.npz -> traj` path: covered by Task 1 and Task 2
- traj-to-step mapping with happy defaults: covered by Task 1 and Task 2
- preparation and finish motions: covered by Task 1 and Task 3
- standalone CLI: covered by Task 4 and Task 5
- `--dry-run`, `--print-summary`, and `--save-traj`: covered by Task 4, Task 5, and Task 6
- interruption and failure exit codes: covered by Task 4 and Task 5

### Placeholder scan

- no `TODO`, `TBD`, or deferred placeholders remain
- every code-changing step includes concrete code
- every verification step includes an exact command and expected outcome

### Type consistency

- runtime helper names stay consistent across tasks: `build_deterministic_traj`, `summarize_traj`, `write_traj`, `traj_to_steps`, `ModelTrajectoryRunner`
- CLI consistently calls `ModelTrajectoryRunner.run_model(model_path, dry_run=..., save_traj_path=...)`
- step dictionaries consistently use the existing runtime keys: `mode`, `gait_id`, `velocity`, `step_height`, `body_height`, `rpy`, `duration`
