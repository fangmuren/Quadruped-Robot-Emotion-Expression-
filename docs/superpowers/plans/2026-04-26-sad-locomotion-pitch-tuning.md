# Sad Locomotion Pitch Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tune the three `sad` locomotion steps so the backward walk stays visible while the low-head feeling remains more apparent after locomotion takeover.

**Architecture:** Keep the current runtime and sequencing unchanged and perform the tuning entirely in configuration. First lock the intended first-pass tuning values in tests, then update only the three `mode=11, gait_id=27` `sad` locomotion steps in `config_fixed.py` by reducing backward speed while keeping a moderate negative pitch and leaving step height unchanged for this pass.

**Tech Stack:** Python 3, stdlib `unittest`, `pytest` runner, existing emotion config/runtime modules

---

### File Structure

- `config_fixed.py` — source of truth for the three tuned `sad` locomotion steps.
- `tests/test_emotion_contract.py` — contract coverage for the tuned `sad` locomotion parameter values.
- `tests/test_motion_sequence.py` — runtime wiring check that `MotionSequence` emits the tuned locomotion commands in order.

### Task 1: Lock the first-pass tuning values in configuration tests

**Files:**
- Modify: `tests/test_emotion_contract.py`
- Test: `tests/test_emotion_contract.py`

- [ ] **Step 1: Update the `sad` locomotion expectations to require the slower first-pass tuning values**

In `tests/test_emotion_contract.py`, keep the existing `sad` sequence shape assertions and replace only the parameter assertions inside `if emotion == 'sad':` with this block:

```python
            if emotion == 'sad':
                locomotion_steps = config['sequence'][3:6]
                self.assertEqual([step['duration'] for step in locomotion_steps], [450, 450, 400])
                self.assertEqual([step['rpy'][1] for step in locomotion_steps], [-0.12, -0.11, -0.10])
                self.assertEqual([step['velocity'][0] for step in locomotion_steps], [-0.03, -0.03, -0.02])
                self.assertEqual([step['step_height'] for step in locomotion_steps], [[0.02, 0.02], [0.02, 0.02], [0.02, 0.02]])
                self.assertEqual([step['body_height'] for step in locomotion_steps], [0.19, 0.19, 0.19])
```

- [ ] **Step 2: Run the contract test to verify it fails before the config change**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_emotion_contract.py"
```

Expected: FAIL because the active `sad` locomotion steps still use `velocity` values `[-0.04, -0.04, -0.03]` and `rpy` values `[-0.14, -0.12, -0.10]`.

- [ ] **Step 3: Commit the red contract test**

```bash
git add tests/test_emotion_contract.py
git commit -m "test: define sad locomotion tuning contract"
```

### Task 2: Update the runtime test to enforce the tuned command payloads

**Files:**
- Modify: `tests/test_motion_sequence.py`
- Test: `tests/test_motion_sequence.py`

- [ ] **Step 1: Tighten the focused `sad` runtime test to match the tuned locomotion values**

In `tests/test_motion_sequence.py`, update `test_sad_sequence_emits_segmented_low_head_walk_commands` so its locomotion assertions become:

```python
        locomotion = [cmd for cmd in controller.commands if cmd['mode'] == 11 and cmd['gait_id'] == 27]
        self.assertEqual(len(locomotion), 3)
        self.assertEqual([cmd['duration'] for cmd in locomotion], [450, 450, 400])
        self.assertEqual([cmd['rpy'][1] for cmd in locomotion], [-0.12, -0.11, -0.10])
        self.assertEqual([cmd['velocity'][0] for cmd in locomotion], [-0.03, -0.03, -0.02])
        self.assertTrue(all(cmd['step_height'] == [0.02, 0.02] for cmd in locomotion))
        self.assertTrue(all(cmd['body_height'] == 0.19 for cmd in locomotion))
        self.assertEqual(controller.commands[-1]['mode'], 62)
        self.assertEqual(controller.commands[-1]['gait_id'], 3)
```

- [ ] **Step 2: Run the focused runtime test to verify it fails before the config change**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_motion_sequence.py::MotionSequenceTest::test_sad_sequence_emits_segmented_low_head_walk_commands"
```

Expected: FAIL because the emitted `sad` locomotion commands still use the pre-tuning `velocity` and `rpy` values.

- [ ] **Step 3: Commit the red runtime test**

```bash
git add tests/test_motion_sequence.py
git commit -m "test: cover sad locomotion tuning payloads"
```

### Task 3: Apply the first-pass sad locomotion tuning in configuration

**Files:**
- Modify: `config_fixed.py`
- Test: `tests/test_emotion_contract.py`
- Test: `tests/test_motion_sequence.py`

- [ ] **Step 1: Update only the three `sad` locomotion steps to the gentler first-pass values**

In `config_fixed.py`, replace the current three `sad` locomotion blocks:

```python
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.04, 0.0, 0.0],
                'rpy': [0.0, -0.14, 0.0],
                'step_height': [0.02, 0.02],
                'body_height': 0.19,
                'duration': 450,
            },
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.04, 0.0, 0.0],
                'rpy': [0.0, -0.12, 0.0],
                'step_height': [0.02, 0.02],
                'body_height': 0.19,
                'duration': 450,
            },
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.03, 0.0, 0.0],
                'rpy': [0.0, -0.10, 0.0],
                'step_height': [0.02, 0.02],
                'body_height': 0.19,
                'duration': 400,
            },
```

with these tuned first-pass blocks:

```python
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.03, 0.0, 0.0],
                'rpy': [0.0, -0.12, 0.0],
                'step_height': [0.02, 0.02],
                'body_height': 0.19,
                'duration': 450,
            },
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.03, 0.0, 0.0],
                'rpy': [0.0, -0.11, 0.0],
                'step_height': [0.02, 0.02],
                'body_height': 0.19,
                'duration': 450,
            },
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.02, 0.0, 0.0],
                'rpy': [0.0, -0.10, 0.0],
                'step_height': [0.02, 0.02],
                'body_height': 0.19,
                'duration': 400,
            },
```

- [ ] **Step 2: Run the focused contract and runtime tests to verify the tuning passes**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_emotion_contract.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_motion_sequence.py::MotionSequenceTest::test_sad_sequence_emits_segmented_low_head_walk_commands"
```

Expected: PASS.

- [ ] **Step 3: Run the targeted regression suite**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_config_validation.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_emotion_contract.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_motion_sequence.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_robot_control.py"
```

Expected: PASS with all tests green.

- [ ] **Step 4: Commit the config and green tests**

```bash
git add config_fixed.py tests/test_emotion_contract.py tests/test_motion_sequence.py
git commit -m "tune: soften sad locomotion takeover"
```

### Task 4: Real-robot verification and optional second-pass trigger

**Files:**
- Modify: none in the first-pass verification step
- Test: `config_fixed.py`

- [ ] **Step 1: Run the `sad` emotion on the robot and evaluate the locomotion takeover**

Run:
```bash
python3 /home/grazier/cyberdog_ws/Emotion_dog/main.py sad
```

Expected observable behavior:
- the robot lowers its body
- the robot visibly holds the low-head pose before walking
- the first locomotion segment no longer snaps upright as abruptly as before
- the backward walk remains clearly visible
- the final sit action still looks correct

- [ ] **Step 2: If the first locomotion segment still recenters too quickly, make only the documented second-pass change**

Keep the same three-step structure, `body_height`, and `rpy` values from Task 3, and reduce only `step_height` on those same three blocks from `[0.02, 0.02]` to `[0.015, 0.015]`:

```python
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.03, 0.0, 0.0],
                'rpy': [0.0, -0.12, 0.0],
                'step_height': [0.015, 0.015],
                'body_height': 0.19,
                'duration': 450,
            },
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.03, 0.0, 0.0],
                'rpy': [0.0, -0.11, 0.0],
                'step_height': [0.015, 0.015],
                'body_height': 0.19,
                'duration': 450,
            },
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.02, 0.0, 0.0],
                'rpy': [0.0, -0.10, 0.0],
                'step_height': [0.015, 0.015],
                'body_height': 0.19,
                'duration': 400,
            },
```

Then update the `step_height` assertions in both test files and run:

```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_emotion_contract.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_motion_sequence.py"
```

Expected: PASS before the next real-robot run.

- [ ] **Step 3: Commit the final tuned values after the robot pass**

```bash
git add config_fixed.py tests/test_emotion_contract.py tests/test_motion_sequence.py
git commit -m "tune: preserve sad low-head locomotion"
```