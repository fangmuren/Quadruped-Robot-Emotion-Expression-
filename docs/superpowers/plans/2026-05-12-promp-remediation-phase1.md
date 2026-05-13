# ProMP Runtime Remediation Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix incorrect low/high trajectory metadata and harden the happy ProMP runtime with verifiable summary output, bounded step adaptation, and minimally paced/logged playback.

**Architecture:** Keep the standalone `run_promp_model.py` + `promp_runtime.py` path intact and avoid widening scope into model retraining or general multi-emotion support. Derive `emotion` and `intensity` from the model filename at runtime, then extend the existing runner with small pure helpers for summary output, `velocity_x` mapping into the robot command range `[0.2, 0.4]`, remaining channel clamps, and paced logging so the current happy-only path becomes less fragile without restructuring the codebase.

**Tech Stack:** Python 3.8, `argparse`, `pathlib`, `time`, `unittest`, `pytest`, NumPy

---

## File Structure

- Modify: `promp_runtime.py` — derive runtime labels from model path, map reconstructed `velocity_x` into robot command space, clamp remaining channel values, add minimal pacing/logging hooks to the runner.
- Modify: `run_promp_model.py` — print the model path in summaries and pass a line logger into the runtime runner.
- Modify: `tests/test_promp_runtime.py` — add low/high label regression coverage plus mapping/clamp/pacing/logging tests.
- Modify: `tests/test_run_promp_model.py` — add CLI regression coverage for summary output and runner logger wiring.

## Out of Scope for This Plan

- Expanding the raw/processed dataset.
- Re-fitting `.npz` ProMP models.
- Supporting non-happy schemas or arbitrary channel layouts.
- Closed-loop playback from robot feedback.

### Task 1: Fix runtime metadata labels for low/high models

**Files:**
- Modify: `promp_runtime.py`
- Test: `tests/test_promp_runtime.py`

- [ ] **Step 1: Write the failing runtime metadata regression test**

Add these constants near the existing `MODEL_PATH` constant in `tests/test_promp_runtime.py`:

```python
MODEL_LOW_PATH = PROJECT_ROOT / 'data' / 'happy_promp' / 'models' / 'happy_low_promp.npz'
MODEL_HIGH_PATH = PROJECT_ROOT / 'data' / 'happy_promp' / 'models' / 'happy_high_promp.npz'
```

Add this test method inside `PrompRuntimeDeterministicTrajTest`:

```python
def test_build_deterministic_traj_uses_labels_from_model_path(self):
    low_traj = build_deterministic_traj(MODEL_LOW_PATH)
    high_traj = build_deterministic_traj(MODEL_HIGH_PATH)

    self.assertEqual(low_traj['emotion'], 'happy')
    self.assertEqual(low_traj['intensity'], 'low')
    self.assertEqual(high_traj['emotion'], 'happy')
    self.assertEqual(high_traj['intensity'], 'high')
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/tests/test_promp_runtime.py" \
  -k uses_labels_from_model_path -v
```

Expected: FAIL because `build_deterministic_traj()` returns `'mid'` for both low and high model files.

- [ ] **Step 3: Write the minimal implementation**

In `promp_runtime.py`, add this helper above `build_deterministic_traj()`:

```python
def infer_model_labels(model_path):
    stem = Path(model_path).stem
    parts = stem.split('_')
    if len(parts) >= 3 and parts[-1] == 'promp':
        return parts[0], parts[1]
    return DEFAULT_EMOTION, DEFAULT_INTENSITY
```

Replace `build_deterministic_traj()` with:

```python
def build_deterministic_traj(model_path, sample_id=DEFAULT_SAMPLE_ID, emotion=None, intensity=None):
    model_path = Path(model_path)
    inferred_emotion, inferred_intensity = infer_model_labels(model_path)
    emotion = emotion if emotion is not None else inferred_emotion
    intensity = intensity if intensity is not None else inferred_intensity

    model = load_model(model_path)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m pytest \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/tests/test_promp_runtime.py" \
  -k uses_labels_from_model_path -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor" add \
  promp_runtime.py \
  tests/test_promp_runtime.py && \
git -C "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor" commit -m "fix: derive promp labels from model path"
```

### Task 2: Make CLI summaries verifiable and wire runtime logging into the CLI

**Files:**
- Modify: `run_promp_model.py`
- Test: `tests/test_run_promp_model.py`

- [ ] **Step 1: Write the failing CLI regression tests**

In `tests/test_run_promp_model.py`, add this test method inside `RunPrompModelCliTest`:

```python
def test_main_prints_model_path_in_summary(self):
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
    self.assertIn(f'model_path={MODEL_PATH}', stdout.getvalue())
```

Add this test method below it:

```python
def test_main_passes_logger_into_runner(self):
    fake_result = {
        'status': 'dry_run',
        'summary': {
            'n_frames': 45,
            'dt_ms': 50,
            'total_duration_ms': 2200,
            'channel_ranges': {},
        },
    }

    with mock.patch('run_promp_model.ModelTrajectoryRunner') as runner_cls:
        runner_cls.return_value.run_model.return_value = fake_result
        exit_code = run_promp_model.main([str(MODEL_PATH), '--dry-run'])

    self.assertEqual(exit_code, 0)
    self.assertIn('log_fn', runner_cls.call_args.kwargs)
    self.assertTrue(callable(runner_cls.call_args.kwargs['log_fn']))
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/tests/test_run_promp_model.py" \
  -k "model_path_in_summary or passes_logger_into_runner" -v
```

Expected:
- the summary test fails because `model_path=` is missing from the output;
- the logger wiring test fails because `ModelTrajectoryRunner()` is currently called with no keyword arguments.

- [ ] **Step 3: Write the minimal implementation**

In `run_promp_model.py`, replace `_write_summary()` with:

```python
def _write_summary(stdout, model_path, result):
    summary = result['summary']
    stdout.write(f"model_path={model_path}\n")
    stdout.write(f"status={result['status']}\n")
    stdout.write(f"n_frames={summary['n_frames']}\n")
    stdout.write(f"dt_ms={summary['dt_ms']}\n")
    stdout.write(f"total_duration_ms={summary['total_duration_ms']}\n")
    for channel_name in sorted(summary['channel_ranges']):
        channel_range = summary['channel_ranges'][channel_name]
        stdout.write(
            f"{channel_name}: min={channel_range['min']}, max={channel_range['max']}\n"
        )
```

In `main()`, replace the runner creation with:

```python
    stream = stdout or sys.stdout
    runner = ModelTrajectoryRunner(
        log_fn=lambda line: stream.write(f"{line}\n"),
    )
```

Replace the summary call with:

```python
    if args.print_summary:
        _write_summary(stream, args.model_npz, result)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m pytest \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/tests/test_run_promp_model.py" \
  -k "model_path_in_summary or passes_logger_into_runner" -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor" add \
  run_promp_model.py \
  tests/test_run_promp_model.py && \
git -C "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor" commit -m "fix: improve promp cli summary output"
```

### Task 3: Map `velocity_x` into robot command space `[0.2, 0.4]` and clamp the remaining fields

**Files:**
- Modify: `promp_runtime.py`
- Test: `tests/test_promp_runtime.py`

**Context:** The user confirmed that robot-side `velocity_x` for this path must stay in `[0.2, 0.4]`. The current processed happy trajectories span roughly `0.03` to `0.088889`, so this task treats ProMP `velocity_x` as trajectory-space output that must be linearly mapped into robot command space before dispatch.

- [ ] **Step 1: Write the failing adapter regression tests**

In `tests/test_promp_runtime.py`, add this test method inside `PrompRuntimeAdapterTest`:

```python
def test_traj_to_steps_maps_velocity_x_into_robot_range_and_clamps_other_channels(self):
    traj = {
        'dt_ms': 50,
        'n_frames': 2,
        'phase': [0.0, 1.0],
        'time_ms': [0, 50],
        'channels': {
            'velocity_x': [0.03, 0.088889],
            'yaw_rate': [-0.4, 0.4],
            'step_height_front': [0.2, 0.01],
            'step_height_hind': [-0.1, 0.2],
            'body_height': [0.35, 0.2],
            'pitch': [0.4, -0.2],
        },
    }

    steps = traj_to_steps(traj)

    self.assertEqual(steps, [
        {
            'mode': 11,
            'gait_id': 27,
            'velocity': [0.2, 0.0, -0.25],
            'step_height': [0.05, 0.0],
            'body_height': 0.27,
            'rpy': [0.0, 0.2, 0.0],
            'duration': 50,
        },
        {
            'mode': 11,
            'gait_id': 27,
            'velocity': [0.4, 0.0, 0.25],
            'step_height': [0.01, 0.05],
            'body_height': 0.22,
            'rpy': [0.0, -0.05, 0.0],
            'duration': 50,
        },
    ])
```

Add this test method inside `PrompRuntimeDeterministicTrajTest`:

```python
def test_low_model_steps_use_robot_velocity_range(self):
    traj = build_deterministic_traj(MODEL_LOW_PATH)
    steps = traj_to_steps(traj)

    self.assertTrue(all(0.2 <= step['velocity'][0] <= 0.4 for step in steps))
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/tests/test_promp_runtime.py" \
  -k "maps_velocity_x_into_robot_range_and_clamps_other_channels or low_model_steps_use_robot_velocity_range" -v
```

Expected: FAIL because `traj_to_steps()` currently copies the reconstructed values through unchanged.

- [ ] **Step 3: Write the minimal implementation**

In `promp_runtime.py`, add these constants under `REQUIRED_CHANNELS`:

```python
VELOCITY_X_SOURCE_RANGE = (0.03, 0.088889)
VELOCITY_X_TARGET_RANGE = (0.2, 0.4)
CHANNEL_LIMITS = {
    'yaw_rate': (-0.25, 0.25),
    'step_height_front': (0.0, 0.05),
    'step_height_hind': (0.0, 0.05),
    'body_height': (0.22, 0.27),
    'pitch': (-0.05, 0.2),
}
```

Add these helpers below `_validate_traj()`:

```python
def clamp_value(value, lower, upper):
    return max(lower, min(upper, value))


def map_velocity_x(value):
    source_min, source_max = VELOCITY_X_SOURCE_RANGE
    target_min, target_max = VELOCITY_X_TARGET_RANGE
    if source_max == source_min:
        return target_min
    normalized = (value - source_min) / (source_max - source_min)
    normalized = clamp_value(normalized, 0.0, 1.0)
    return round(target_min + normalized * (target_max - target_min), 6)


def clamp_channel_value(channel_name, value):
    lower, upper = CHANNEL_LIMITS[channel_name]
    return clamp_value(value, lower, upper)
```

Then replace the body of `traj_to_steps()` with:

```python
def traj_to_steps(traj):
    _validate_traj(traj)
    steps = []
    channels = traj['channels']
    for index in range(traj['n_frames']):
        velocity_x = map_velocity_x(channels['velocity_x'][index])
        yaw_rate = clamp_channel_value('yaw_rate', channels['yaw_rate'][index])
        step_height_front = clamp_channel_value('step_height_front', channels['step_height_front'][index])
        step_height_hind = clamp_channel_value('step_height_hind', channels['step_height_hind'][index])
        body_height = clamp_channel_value('body_height', channels['body_height'][index])
        pitch = clamp_channel_value('pitch', channels['pitch'][index])

        steps.append({
            'mode': DEFAULT_MODE,
            'gait_id': DEFAULT_GAIT_ID,
            'velocity': [velocity_x, DEFAULT_VELOCITY_Y, yaw_rate],
            'step_height': [step_height_front, step_height_hind],
            'body_height': body_height,
            'rpy': [DEFAULT_RPY_ROLL, pitch, DEFAULT_RPY_YAW],
            'duration': traj['dt_ms'],
        })
    return steps
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m pytest \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/tests/test_promp_runtime.py" \
  -k "maps_velocity_x_into_robot_range_and_clamps_other_channels or low_model_steps_use_robot_velocity_range" -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor" add \
  promp_runtime.py \
  tests/test_promp_runtime.py && \
git -C "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor" commit -m "fix: map promp velocity into robot range"
```

### Task 4: Add minimal pacing and coarse runtime logging to playback

**Files:**
- Modify: `promp_runtime.py`
- Test: `tests/test_promp_runtime.py`

- [ ] **Step 1: Write the failing pacing/logging runner test**

In `tests/test_promp_runtime.py`, add this test method inside `PrompRuntimeRunnerTest`:

```python
def test_runner_paces_frames_and_emits_coarse_logs(self):
    controller = FakeController()
    sleeps = []
    logs = []
    traj = make_two_frame_runner_traj()
    runner = ModelTrajectoryRunner(
        controller_factory=lambda: controller,
        sleep_fn=sleeps.append,
        log_fn=logs.append,
    )

    result = runner.run_traj(traj)

    self.assertEqual(result['status'], 'completed')
    self.assertEqual(sleeps, [0.05, 0.05])
    self.assertEqual(logs[0], 'controller_start')
    self.assertIn('preparation_start', logs)
    self.assertIn('playback_start n_frames=2 dt_ms=50', logs)
    self.assertIn('playback_frame=1/2', logs)
    self.assertIn('playback_frame=2/2', logs)
    self.assertIn('finish_start', logs)
    self.assertEqual(logs[-1], 'controller_shutdown')
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/tests/test_promp_runtime.py" \
  -k paces_frames_and_emits_coarse_logs -v
```

Expected: FAIL because `ModelTrajectoryRunner.__init__()` does not accept `sleep_fn`/`log_fn`, and `run_traj()` never sleeps or emits progress messages.

- [ ] **Step 3: Write the minimal implementation**

In `promp_runtime.py`, add `import time` at the top and replace `ModelTrajectoryRunner` with:

```python
class ModelTrajectoryRunner:
    def __init__(self, controller_factory=None, sleep_fn=None, log_fn=None):
        self.controller_factory = controller_factory
        self.sleep_fn = sleep_fn or time.sleep
        self.log_fn = log_fn or (lambda line: None)

    def _log(self, line):
        self.log_fn(line)

    def _create_controller(self):
        if self.controller_factory is not None:
            return self.controller_factory()
        from robot_control import CyberDogController
        return CyberDogController()

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

        self._log('controller_start')
        controller = self._create_controller()
        try:
            self._log('preparation_start')
            for step in DEFAULT_PREPARATION_STEPS:
                controller.send_command(**step)

            self._log(f"playback_start n_frames={len(steps)} dt_ms={traj['dt_ms']}")
            for index, step in enumerate(steps):
                controller.send_command(**step)
                if index % 10 == 0 or index == len(steps) - 1:
                    self._log(f'playback_frame={index + 1}/{len(steps)}')
                self.sleep_fn(step['duration'] / 1000.0)

            self._log('finish_start')
            controller.send_command(**DEFAULT_FINISH_STEP)
            self._log('completed')
            return {
                'status': 'completed',
                'traj': traj,
                'steps': steps,
                'summary': summary,
            }
        except KeyboardInterrupt:
            try:
                controller.send_command(**DEFAULT_FINISH_STEP)
            except Exception:
                pass
            self._log('interrupted')
            raise
        except Exception:
            try:
                controller.send_command(**DEFAULT_FINISH_STEP)
            except Exception:
                pass
            self._log('failed')
            raise
        finally:
            controller.close()
            self._log('controller_shutdown')
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m pytest \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/tests/test_promp_runtime.py" \
  -k paces_frames_and_emits_coarse_logs -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor" add \
  promp_runtime.py \
  tests/test_promp_runtime.py && \
git -C "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor" commit -m "feat: pace and log promp playback"
```

### Task 5: Run the full ProMP verification set

**Files:**
- Verify: `tests/test_promp_runtime.py`
- Verify: `tests/test_run_promp_model.py`
- Verify: `tests/test_happy_promp_data_pipeline.py`

- [ ] **Step 1: Run the full ProMP pytest set**

Run:

```bash
python3 -m pytest \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/tests/test_promp_runtime.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/tests/test_run_promp_model.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/tests/test_happy_promp_data_pipeline.py"
```

Expected: all tests PASS.

- [ ] **Step 2: Run real dry-run checks on low and high models and inspect the output files**

Run:

```bash
python3 "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/run_promp_model.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/data/happy_promp/models/happy_low_promp.npz" \
  --dry-run --print-summary --save-traj "/tmp/happy_low_runtime_check.traj.json"

python3 "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/run_promp_model.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor/data/happy_promp/models/happy_high_promp.npz" \
  --dry-run --print-summary --save-traj "/tmp/happy_high_runtime_check.traj.json"
```

Expected:
- summary output includes `model_path=`;
- both runs exit cleanly;
- `/tmp/happy_low_runtime_check.traj.json` contains `"intensity": "low"`;
- `/tmp/happy_high_runtime_check.traj.json` contains `"intensity": "high"`.

- [ ] **Step 3: Verify the generated robot step velocities stay inside `[0.2, 0.4]`**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
from promp_runtime import build_deterministic_traj, traj_to_steps

root = Path('/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor')
for name in ['happy_low_promp.npz', 'happy_mid_promp.npz', 'happy_high_promp.npz']:
    traj = build_deterministic_traj(root / 'data' / 'happy_promp' / 'models' / name)
    steps = traj_to_steps(traj)
    values = [step['velocity'][0] for step in steps]
    print(name, min(values), max(values))
PY
```

Expected:
- every printed minimum is `>= 0.2`;
- every printed maximum is `<= 0.4`.

- [ ] **Step 4: Commit the finished phase-1 runtime hardening work**

```bash
git -C "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor" add \
  promp_runtime.py \
  run_promp_model.py \
  tests/test_promp_runtime.py \
  tests/test_run_promp_model.py && \
git -C "/home/grazier/cyberdog_ws/Emotion_dog/.claude/worktrees/traj-to-robot-executor" commit -m "fix: harden promp runtime playback"
```
