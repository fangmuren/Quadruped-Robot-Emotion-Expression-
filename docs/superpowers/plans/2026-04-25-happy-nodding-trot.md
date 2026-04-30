# Happy Nodding Trot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the `happy` emotion so its trot lasts 2500ms and performs a visible nodding motion by splitting the trot into short locomotion steps with changing pitch.

**Architecture:** Keep the existing execution model unchanged. Implement the nodding behavior entirely in configuration by replacing the single `happy` locomotion step with a sequence of short `mode=11, gait_id=10` steps that preserve speed, step height, and body height while varying `rpy[1]` across a bounded oscillation.

**Tech Stack:** Python 3, stdlib `unittest`, existing emotion config/runtime modules

---

### Task 1: Lock the new happy sequence contract in tests

**Files:**
- Modify: `tests/test_emotion_contract.py`
- Test: `tests/test_emotion_contract.py`

- [ ] **Step 1: Write the failing test expectations for the expanded happy locomotion sequence**

```python
'happy': {
    'type': 'loop',
    'modes': [12, 21, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 62],
    'gaits': [0, 5, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 4],
    'stop_mode': 3,
}
```

Also add assertions that the 10 locomotion steps:

```python
locomotion_steps = config['sequence'][2:12]
self.assertEqual([step['duration'] for step in locomotion_steps], [250] * 10)
self.assertEqual(sum(step['duration'] for step in locomotion_steps), 2500)
self.assertEqual([step['rpy'][1] for step in locomotion_steps], [-0.10, -0.04, 0.02, 0.08, 0.12, 0.06, 0.00, -0.05, -0.10, -0.02])
```

- [ ] **Step 2: Run the contract test to verify it fails before the config change**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_emotion_contract.py"
```

Expected: FAIL because `happy` still contains a single locomotion step and does not expose the new pitch sequence.

- [ ] **Step 3: Commit the red test if working in a dedicated branch flow**

```bash
git add tests/test_emotion_contract.py
git commit -m "test: define happy nodding trot contract"
```

### Task 2: Replace the single happy trot step with nodding locomotion steps

**Files:**
- Modify: `config_fixed.py`
- Test: `tests/test_emotion_contract.py`

- [ ] **Step 1: Replace the single trot step in `happy.sequence` with 10 short locomotion steps**

Use this exact block in `config_fixed.py`:

```python
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, -0.10, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, -0.04, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, 0.02, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, 0.08, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, 0.12, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, 0.06, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, 0.00, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, -0.05, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, -0.10, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, -0.02, 0.0],
                'duration': 250,
            },
```

- [ ] **Step 2: Run the contract test to verify the config now matches the new happy sequence**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_emotion_contract.py"
```

Expected: PASS.

- [ ] **Step 3: Commit the config change**

```bash
git add config_fixed.py tests/test_emotion_contract.py
git commit -m "feat: extend happy trot with nodding motion"
```

### Task 3: Verify runtime wiring still accepts the expanded happy sequence

**Files:**
- Modify: `tests/test_motion_sequence.py`
- Test: `tests/test_motion_sequence.py`

- [ ] **Step 1: Add a runtime test that inspects the happy locomotion burst**

Add a test like this:

```python
def test_happy_sequence_contains_2500ms_nodding_trot_burst(self):
    controller = FakeController()
    sequencer = MotionSequence(controller)

    sequencer.execute_emotion('happy')
    time.sleep(0.05)
    sequencer.stop()

    locomotion = [cmd for cmd in controller.commands if cmd['mode'] == 11 and cmd['gait_id'] == 10]
    self.assertEqual(len(locomotion), 10)
    self.assertEqual([cmd['duration'] for cmd in locomotion], [250] * 10)
    self.assertEqual([cmd['rpy'][1] for cmd in locomotion], [-0.10, -0.04, 0.02, 0.08, 0.12, 0.06, 0.00, -0.05, -0.10, -0.02])
```

- [ ] **Step 2: Run the runtime test to verify it fails before the new config is in place, or passes after Task 2**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_motion_sequence.py::MotionSequenceTest::test_happy_sequence_contains_2500ms_nodding_trot_burst"
```

Expected after Task 2: PASS.

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

- [ ] **Step 4: Commit the verification test update**

```bash
git add tests/test_motion_sequence.py
git commit -m "test: cover happy nodding trot execution"
```
