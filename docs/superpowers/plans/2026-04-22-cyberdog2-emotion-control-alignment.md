# CyberDog2 Emotion Control Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the active CyberDog2 emotion-control code with `六情绪动作开发.pdf`, remove dead files, make the motion flow easy to modify, and fix the loop/stop logic so local tests can verify behavior without robot hardware.

**Architecture:** Keep the existing direct-control architecture. Put PDF-driven emotion definitions in `config.py`, keep emotion naming and lookup in `emotion.py`, centralize sequencing behavior in `motion_sequence.py`, and keep `main.py`/`demo.py` as thin orchestration layers. Use local fake-controller tests to lock the behavior before touching robot-dependent code.

**Tech Stack:** Python 3, standard-library `unittest`, LCM message wrappers already in repo, `pdftotext` from poppler-utils for reference extraction during implementation.

---

## File Structure

### Files to delete
- `scripts/demo_refined_v1.py`
- `scripts/demo_rule_v1.py`
- `scripts/auto_lcm_init.sh:Zone.Identifier`

### Files to modify
- `config.py`
- `emotion.py`
- `motion_sequence.py`
- `main.py`
- `demo.py`
- `robot_control.py`

### Files to create
- `tests/__init__.py`
- `tests/test_emotion_contract.py`
- `tests/test_motion_sequence.py`
- `tests/test_runtime_policy.py`

## PDF-Derived Target Contract

Use these six canonical emotions and remove the extra two current ones:
- `happy`
- `sad`
- `fearful`
- `angry`
- `disgusted`
- `surprised`

Use these target configuration decisions, chosen directly from the PDF ranges so the code has one explicit implementation to test:

- `happy`: loop; forward locomotion with an upbeat body height, then `mode=144` as a signature action; `stop_motion` returns to stable stand.
- `sad`: single; lower body with slight forward-down pitch, slow low-energy retreat, then `mode=143` sit.
- `fearful`: single; lower body, short backward retreat, two small pose tremors, then angle away.
- `angry`: single; short forward-press pose, fast straight approach burst, then two short forward pressure pulses and a rigid stand.
- `disgusted`: single; short recoil, turn-away, two quick body sways, then hold side-turned posture.
- `surprised`: single; fast raise-and-orient move, short freeze, then return to neutral-height stand.

Use these explicit numeric defaults in `config.py`:

```python
PDF_EMOTION_CONFIGS = {
    'happy': {
        'type': 'loop',
        'demo_seconds': 6.0,
        'sequence': [
            {'mode': 12, 'gait_id': 0, 'duration': 800},
            {'mode': 11, 'gait_id': 303, 'velocity': [0.40, 0.0, 0.0], 'step_height': [0.04, 0.04], 'body_height': 0.24, 'duration': 1500},
            {'mode': 144, 'gait_id': 0, 'duration': 1200},
        ],
        'stop_motion': {'mode': 3, 'gait_id': 0, 'body_height': 0.22, 'duration': 600},
    },
    'sad': {
        'type': 'single',
        'demo_seconds': 4.0,
        'sequence': [
            {'mode': 12, 'gait_id': 0, 'duration': 800},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.19], 'rpy': [0.0, -0.12, 0.0], 'duration': 1600},
            {'mode': 11, 'gait_id': 303, 'velocity': [-0.05, 0.0, 0.0], 'step_height': [0.02, 0.02], 'body_height': 0.19, 'duration': 1200},
            {'mode': 143, 'gait_id': 0, 'duration': 1800},
        ],
    },
    'fearful': {
        'type': 'single',
        'demo_seconds': 4.0,
        'sequence': [
            {'mode': 21, 'gait_id': 0, 'position': [-0.02, 0.0, 0.20], 'rpy': [0.0, -0.08, 0.0], 'duration': 500},
            {'mode': 11, 'gait_id': 303, 'velocity': [-0.22, 0.0, 0.0], 'step_height': [0.015, 0.015], 'body_height': 0.20, 'duration': 1100},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.20], 'rpy': [0.02, -0.08, 0.05], 'duration': 220},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.20], 'rpy': [-0.02, -0.08, -0.05], 'duration': 220},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.20], 'rpy': [0.0, -0.08, 0.35], 'duration': 500},
        ],
    },
    'angry': {
        'type': 'single',
        'demo_seconds': 3.0,
        'sequence': [
            {'mode': 12, 'gait_id': 0, 'duration': 800},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.23], 'rpy': [0.0, -0.12, 0.0], 'duration': 500},
            {'mode': 11, 'gait_id': 305, 'velocity': [0.80, 0.0, 0.0], 'step_height': [0.05, 0.05], 'body_height': 0.23, 'duration': 900},
            {'mode': 21, 'gait_id': 0, 'position': [0.02, 0.0, 0.23], 'rpy': [0.0, -0.14, 0.0], 'duration': 180},
            {'mode': 21, 'gait_id': 0, 'position': [0.02, 0.0, 0.23], 'rpy': [0.0, -0.14, 0.0], 'duration': 180},
            {'mode': 3, 'gait_id': 0, 'body_height': 0.23, 'duration': 800},
        ],
    },
    'disgusted': {
        'type': 'single',
        'demo_seconds': 3.0,
        'sequence': [
            {'mode': 21, 'gait_id': 0, 'position': [-0.02, 0.0, 0.22], 'rpy': [0.0, 0.0, 0.0], 'duration': 400},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.22], 'rpy': [0.0, 0.0, 0.50], 'duration': 450},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.22], 'rpy': [0.04, 0.0, 0.28], 'duration': 220},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.22], 'rpy': [-0.04, 0.0, 0.28], 'duration': 220},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.22], 'rpy': [0.0, 0.0, 0.28], 'duration': 800},
        ],
    },
    'surprised': {
        'type': 'single',
        'demo_seconds': 2.0,
        'sequence': [
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.25], 'rpy': [0.0, 0.10, 0.30], 'duration': 280},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.25], 'rpy': [0.0, 0.10, 0.30], 'duration': 700},
            {'mode': 3, 'gait_id': 0, 'body_height': 0.22, 'duration': 500},
        ],
    },
}
```

## Task 1: Lock the six-emotion contract and runtime policy

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_emotion_contract.py`
- Modify: `emotion.py`
- Modify: `config.py`

- [ ] **Step 1: Write the failing contract test**

```python
import unittest

from emotion import SixEmotions, get_all_emotions, get_emotion_config


class EmotionContractTest(unittest.TestCase):
    def test_exports_exactly_six_pdf_emotions(self):
        self.assertEqual(
            get_all_emotions(),
            ['happy', 'sad', 'fearful', 'angry', 'disgusted', 'surprised'],
        )
        self.assertEqual(SixEmotions.ALL, get_all_emotions())

    def test_removed_emotions_are_not_available(self):
        with self.assertRaises(ValueError):
            get_emotion_config('confused')
        with self.assertRaises(ValueError):
            get_emotion_config('lost')

    def test_every_emotion_has_runtime_metadata(self):
        expected = {
            'happy': ('loop', 6.0),
            'sad': ('single', 4.0),
            'fearful': ('single', 4.0),
            'angry': ('single', 3.0),
            'disgusted': ('single', 3.0),
            'surprised': ('single', 2.0),
        }
        for emotion, pair in expected.items():
            config = get_emotion_config(emotion)
            self.assertEqual((config['type'], config['demo_seconds']), pair)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the contract test and verify it fails**

Run:

```bash
python3 -m unittest discover -s tests -p "test_emotion_contract.py" -v
```

Expected: FAIL because `emotion.py` still exports eight emotions and `config.py` has no `demo_seconds` field.

- [ ] **Step 3: Add the minimal implementation to pass the contract test**

Create `tests/__init__.py` as an empty file.

Update `emotion.py` to:

```python
from config import EMOTION_CONFIGS


class SixEmotions:
    HAPPY = 'happy'
    SAD = 'sad'
    FEARFUL = 'fearful'
    ANGRY = 'angry'
    DISGUSTED = 'disgusted'
    SURPRISED = 'surprised'

    ALL = [HAPPY, SAD, FEARFUL, ANGRY, DISGUSTED, SURPRISED]


def get_emotion_config(emotion: str) -> dict:
    if emotion not in EMOTION_CONFIGS:
        raise ValueError(f"Unknown emotion: {emotion}. Must be one of {SixEmotions.ALL}")
    return EMOTION_CONFIGS[emotion]


def get_all_emotions() -> list:
    return SixEmotions.ALL
```

Update `config.py` so `EMOTION_CONFIGS` is exactly the `PDF_EMOTION_CONFIGS` table from this plan and remove `CONFUSED` and `LOST` entirely.

- [ ] **Step 4: Re-run the contract test and verify it passes**

Run:

```bash
python3 -m unittest discover -s tests -p "test_emotion_contract.py" -v
```

Expected: PASS with 3 tests.

- [ ] **Step 5: Local checkpoint**

Run:

```bash
python3 -m py_compile config.py emotion.py
```

Expected: no output.

## Task 2: Lock the PDF-driven sequence details in tests

**Files:**
- Modify: `tests/test_emotion_contract.py`
- Modify: `config.py`

- [ ] **Step 1: Extend the failing test with exact sequence expectations**

Append to `tests/test_emotion_contract.py`:

```python
    def test_pdf_sequences_match_expected_signature(self):
        expected = {
            'happy': {
                'type': 'loop',
                'modes': [12, 11, 144],
                'gaits': [0, 303, 0],
                'stop_mode': 3,
            },
            'sad': {
                'type': 'single',
                'modes': [12, 21, 11, 143],
                'gaits': [0, 0, 303, 0],
            },
            'fearful': {
                'type': 'single',
                'modes': [21, 11, 21, 21, 21],
                'gaits': [0, 0, 0, 0, 0],
            },
            'angry': {
                'type': 'single',
                'modes': [12, 21, 11, 21, 21, 3],
                'gaits': [0, 0, 305, 0, 0, 0],
            },
            'disgusted': {
                'type': 'single',
                'modes': [21, 21, 21, 21, 21],
                'gaits': [0, 0, 0, 0, 0],
            },
            'surprised': {
                'type': 'single',
                'modes': [21, 21, 3],
                'gaits': [0, 0, 0],
            },
        }

        for emotion, spec in expected.items():
            config = get_emotion_config(emotion)
            self.assertEqual(config['type'], spec['type'])
            self.assertEqual([step['mode'] for step in config['sequence']], spec['modes'])
            self.assertEqual([step.get('gait_id', 0) for step in config['sequence']], spec['gaits'])
            if 'stop_mode' in spec:
                self.assertEqual(config['stop_motion']['mode'], spec['stop_mode'])
```

- [ ] **Step 2: Run the contract test and verify it fails if any sequence differs**

Run:

```bash
python3 -m unittest discover -s tests -p "test_emotion_contract.py" -v
```

Expected: FAIL until `config.py` exactly matches the sequence table in this plan.

- [ ] **Step 3: Make the minimum sequence corrections in `config.py`**

Keep `config.py` as a plain data file. Do not add helper classes. Ensure every step uses the exact `mode`, `gait_id`, `duration`, `velocity`, `position`, `rpy`, `body_height`, and `step_height` values from the `PDF_EMOTION_CONFIGS` table in this plan.

- [ ] **Step 4: Re-run the contract test and verify it passes**

Run:

```bash
python3 -m unittest discover -s tests -p "test_emotion_contract.py" -v
```

Expected: PASS with 4 tests.

- [ ] **Step 5: Local checkpoint**

Run:

```bash
python3 -m py_compile config.py emotion.py tests/test_emotion_contract.py
```

Expected: no output.

## Task 3: Fix motion sequencing with test-first loop/stop coverage

**Files:**
- Create: `tests/test_motion_sequence.py`
- Modify: `motion_sequence.py`

- [ ] **Step 1: Write the failing sequencing tests**

Create `tests/test_motion_sequence.py`:

```python
import time
import unittest

from motion_sequence import MotionSequence


class FakeController:
    def __init__(self):
        self.commands = []

    def send_command(self, **kwargs):
        self.commands.append(kwargs.copy())


class MotionSequenceTest(unittest.TestCase):
    def test_single_emotion_runs_synchronously_and_resets_state(self):
        controller = FakeController()
        sequencer = MotionSequence(controller)

        sequencer.execute_emotion('sad')

        self.assertFalse(sequencer.is_running())
        self.assertEqual(sequencer.current_emotion, 'sad')
        self.assertEqual([cmd['mode'] for cmd in controller.commands], [12, 21, 11, 143])

    def test_loop_emotion_runs_in_background_until_stopped(self):
        controller = FakeController()
        sequencer = MotionSequence(controller)

        sequencer.execute_emotion('happy')
        time.sleep(0.2)
        self.assertTrue(sequencer.is_running())
        self.assertGreaterEqual(len(controller.commands), 1)

        sequencer.stop()

        self.assertFalse(sequencer.is_running())
        self.assertEqual(controller.commands[-1]['mode'], 3)

    def test_stop_without_active_loop_is_safe(self):
        controller = FakeController()
        sequencer = MotionSequence(controller)

        sequencer.stop()

        self.assertFalse(sequencer.is_running())
        self.assertEqual(controller.commands, [])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the sequencing tests and verify they fail**

Run:

```bash
python3 -m unittest discover -s tests -p "test_motion_sequence.py" -v
```

Expected: FAIL because loop execution is currently blocking and state does not reset correctly.

- [ ] **Step 3: Implement the minimum asynchronous loop worker in `motion_sequence.py`**

Update `motion_sequence.py` to this structure:

```python
import threading
import time
from config import EMOTION_CONFIGS


class MotionSequence:
    def __init__(self, controller):
        self.controller = controller
        self.current_emotion = None
        self.is_executing = False
        self._stop_requested = False
        self._worker = None
        self._lock = threading.Lock()

    def execute_emotion(self, emotion: str):
        if emotion not in EMOTION_CONFIGS:
            raise ValueError(f"Unknown emotion: {emotion}")
        if self.is_running():
            raise RuntimeError("Another emotion is already running")

        config = EMOTION_CONFIGS[emotion]
        self.current_emotion = emotion
        self._stop_requested = False
        self.is_executing = True

        if config['type'] == 'single':
            try:
                self._execute_single(config['sequence'])
            finally:
                self.is_executing = False
            return

        self._worker = threading.Thread(
            target=self._run_loop_emotion,
            args=(config['sequence'], config.get('stop_motion')),
            daemon=True,
        )
        self._worker.start()

    def _run_loop_emotion(self, sequence, stop_motion):
        try:
            while not self._stop_requested:
                for step in sequence:
                    if self._stop_requested:
                        break
                    self._execute_step(step)
            if stop_motion:
                self._execute_step(stop_motion)
        finally:
            self.is_executing = False
            self._worker = None

    def _execute_single(self, sequence):
        for step in sequence:
            if self._stop_requested:
                break
            self._execute_step(step)

    def _execute_step(self, step):
        self.controller.send_command(
            mode=step['mode'],
            gait_id=step.get('gait_id', 0),
            velocity=step.get('velocity', [0, 0, 0]),
            step_height=step.get('step_height', [0, 0]),
            body_height=step.get('body_height', 0.20),
            position=step.get('position', [0, 0, 0]),
            rpy=step.get('rpy', [0, 0, 0]),
            duration=step.get('duration', 0),
        )
        duration = step.get('duration', 0)
        if duration > 0:
            time.sleep(duration / 1000.0)

    def stop(self):
        self._stop_requested = True
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=5.0)
        if worker is None:
            self.is_executing = False

    def is_running(self):
        return self.is_executing
```

- [ ] **Step 4: Re-run the sequencing tests and verify they pass**

Run:

```bash
python3 -m unittest discover -s tests -p "test_motion_sequence.py" -v
```

Expected: PASS with 3 tests.

- [ ] **Step 5: Local checkpoint**

Run:

```bash
python3 -m py_compile motion_sequence.py tests/test_motion_sequence.py
```

Expected: no output.

## Task 4: Remove hard-coded runtime branching from the entrypoints

**Files:**
- Create: `tests/test_runtime_policy.py`
- Modify: `main.py`
- Modify: `demo.py`
- Modify: `config.py`

- [ ] **Step 1: Write the failing runtime-policy tests**

Create `tests/test_runtime_policy.py`:

```python
import unittest

from config import EMOTION_CONFIGS


def get_runtime_policy(emotion):
    config = EMOTION_CONFIGS[emotion]
    return config['type'], config['demo_seconds']


class RuntimePolicyTest(unittest.TestCase):
    def test_runtime_policy_is_configuration_driven(self):
        self.assertEqual(get_runtime_policy('happy'), ('loop', 6.0))
        self.assertEqual(get_runtime_policy('sad'), ('single', 4.0))
        self.assertEqual(get_runtime_policy('surprised'), ('single', 2.0))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the runtime-policy test and verify it fails only if metadata is missing**

Run:

```bash
python3 -m unittest discover -s tests -p "test_runtime_policy.py" -v
```

Expected: PASS already after Task 1. Keep it as a guard before touching `main.py` and `demo.py`.

- [ ] **Step 3: Simplify `main.py` and `demo.py` to use configuration metadata**

Update the non-loop branch in `main.py` to:

```python
        config = EMOTION_CONFIGS[args.emotion]
        runtime_type = config['type']
        demo_seconds = config['demo_seconds']

        if args.loop:
            print("循环模式，按 Ctrl+C 停止")
            while sequencer.is_running():
                time.sleep(0.1)
        elif runtime_type == 'single':
            time.sleep(demo_seconds)
        else:
            print(f"演示 {demo_seconds:.0f} 秒后停止...")
            time.sleep(demo_seconds)
            sequencer.stop()
```

Update `demo.py` loop to:

```python
        for emotion in SixEmotions.ALL:
            config = get_emotion_config(emotion)
            print(f"\n{'='*60}")
            print(f">>> 执行情绪: {emotion} (类型: {config['type']})")
            print(f"{'='*60}")

            sequencer.execute_emotion(emotion)
            time.sleep(config['demo_seconds'])
            if config['type'] == 'loop':
                sequencer.stop()
                time.sleep(0.5)

            print(f">>> {emotion} 执行完成\n")
```

Also add this import to `main.py`:

```python
from config import EMOTION_CONFIGS
```

- [ ] **Step 4: Re-run the runtime-policy and contract tests**

Run:

```bash
python3 -m unittest discover -s tests -p "test_runtime_policy.py" -v && python3 -m unittest discover -s tests -p "test_emotion_contract.py" -v
```

Expected: PASS.

- [ ] **Step 5: Local checkpoint**

Run:

```bash
python3 -m py_compile main.py demo.py config.py tests/test_runtime_policy.py
```

Expected: no output.

## Task 5: Improve transport-layer maintainability without changing protocol behavior

**Files:**
- Modify: `robot_control.py`

- [ ] **Step 1: Write the failing maintainability check as a docstring expectation**

There is no test framework benefit for LCM transport comments alone, so use a one-off check by searching for stale mode and gait comments after editing.

Run before editing:

```bash
grep -n "mode:" "/home/grazier/cyberdog_ws/Emotion_dog/robot_control.py"
```

Expected: existing comment still only lists old low-number gait identifiers and omits the motion IDs used by `config.py`.

- [ ] **Step 2: Update the `send_command` docstring to match the active project vocabulary**

Replace the `Args:` explanation in `robot_control.py` with:

```python
        Args:
            mode: Motion mode or action identifier used by the active emotion configuration.
            gait_id: Gait identifier used by the active emotion configuration.
            velocity: [vx, vy, yaw_rate] target locomotion velocity.
            step_height: [front, back] leg lift height.
            body_height: Body height used when no explicit position is provided.
            position: [x, y, z] position target for pose control motions.
            rpy: [roll, pitch, yaw] orientation target.
            duration: Motion duration in milliseconds; 0 means continue until superseded.
```

- [ ] **Step 3: Verify the stale comment is gone**

Run:

```bash
grep -n "mode:" "/home/grazier/cyberdog_ws/Emotion_dog/robot_control.py"
```

Expected: one concise maintainable docstring description, with no hard-coded outdated enumeration list.

- [ ] **Step 4: Compile the transport module**

Run:

```bash
python3 -m py_compile robot_control.py
```

Expected: no output.

- [ ] **Step 5: Local checkpoint**

Run:

```bash
python3 -m py_compile robot_control.py config.py motion_sequence.py main.py demo.py
```

Expected: no output.

## Task 6: Remove dead files and run the full local verification set

**Files:**
- Delete: `scripts/demo_refined_v1.py`
- Delete: `scripts/demo_rule_v1.py`
- Delete: `scripts/auto_lcm_init.sh:Zone.Identifier`

- [ ] **Step 1: Verify the dead files exist before removing them**

Run:

```bash
ls -la "/home/grazier/cyberdog_ws/Emotion_dog/scripts"
```

Expected: `demo_refined_v1.py`, `demo_rule_v1.py`, and `auto_lcm_init.sh:Zone.Identifier` are present.

- [ ] **Step 2: Remove the dead files**

Run:

```bash
rm "/home/grazier/cyberdog_ws/Emotion_dog/scripts/demo_refined_v1.py" "/home/grazier/cyberdog_ws/Emotion_dog/scripts/demo_rule_v1.py" "/home/grazier/cyberdog_ws/Emotion_dog/scripts/auto_lcm_init.sh:Zone.Identifier"
```

Expected: command succeeds with no output.

- [ ] **Step 3: Run the full local test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: PASS for all tests.

- [ ] **Step 4: Run a final compile check across the active path**

Run:

```bash
python3 -m py_compile config.py emotion.py motion_sequence.py main.py demo.py robot_control.py tests/test_emotion_contract.py tests/test_motion_sequence.py tests/test_runtime_policy.py
```

Expected: no output.

- [ ] **Step 5: Final manual smoke commands**

Run:

```bash
python3 main.py --list && python3 demo.py
```

Expected:
- `main.py --list` prints exactly the six PDF-aligned emotions.
- `demo.py` starts each configured emotion in order. Stop it manually if robot hardware is not available.
```

## Self-Review

- Spec coverage: this plan covers PDF-derived emotion set alignment, maintainability, loop/stop logic, entrypoint cleanup, local tests, and dead-file removal.
- Placeholder scan: no TBD/TODO markers remain.
- Type consistency: the plan uses one consistent six-emotion set and one consistent `demo_seconds` runtime policy.

## Notes

This repository is not a git repository, so the normal commit step is replaced with local verification checkpoints after each task.
