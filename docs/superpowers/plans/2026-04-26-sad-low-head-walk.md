# Sad Low-Head Walk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the `sad` emotion so it holds a visible low-head pose, restores a locomotion-friendly body height, performs a short slow walk with a confirmed positive locomotion pitch, and still ends with the existing sit action.

**Architecture:** Keep the current execution model unchanged and implement the behavior entirely in configuration. Lock the intended `sad` sequence in tests, then preserve the current config shape in `config_fixed.py`: stationary low-head pose with negative pitch, a height-reset step before walking, and a single `mode=11, gait_id=27` locomotion step that uses a moderate positive pitch while walking backward.

**Tech Stack:** Python 3, stdlib `unittest`, `pytest` runner, existing emotion config/runtime modules

---

### File Structure

- `config_fixed.py` — source of truth for the `sad` sequence values.
- `tests/test_emotion_contract.py` — configuration-shape contract for `sad` mode/gait ordering and locomotion parameter expectations.
- `tests/test_motion_sequence.py` — runtime wiring check that `MotionSequence` emits the confirmed sad walk commands in order.

### Task 1: Lock the segmented sad walk contract in configuration tests

**Files:**
- Modify: `tests/test_emotion_contract.py`
- Test: `tests/test_emotion_contract.py`

- [ ] **Step 1: Update the expected `sad` sequence signature to require three locomotion steps**

Replace the current `sad` entry inside `expected = { ... }` with this block:

```python
            'sad': {
                'type': 'single',
                'modes': [12, 21, 21, 11, 11, 11, 62],
                'gaits': [0, 5, 0, 27, 27, 27, 3],
            },
```

Then add this assertion block inside `test_pdf_sequences_match_expected_signature` right after the existing `if emotion == 'happy': ...` section:

```python
            if emotion == 'sad':
                locomotion_steps = config['sequence'][3:6]
                self.assertEqual([step['duration'] for step in locomotion_steps], [450, 450, 400])
                self.assertEqual([step['rpy'][1] for step in locomotion_steps], [-0.14, -0.12, -0.10])
                self.assertEqual([step['velocity'][0] for step in locomotion_steps], [-0.04, -0.04, -0.03])
                self.assertTrue(all(step['body_height'] == 0.19 for step in locomotion_steps))
```

- [ ] **Step 2: Run the contract test to verify it fails before the config change**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_emotion_contract.py"
```

Expected: FAIL because `sad` still contains one `mode=11, gait_id=27` step instead of three segmented locomotion steps.

- [ ] **Step 3: Commit the red contract test**

```bash
git add tests/test_emotion_contract.py
git commit -m "test: define sad low-head walk contract"
```

### Task 2: Add a runtime test for the segmented low-head walk commands

**Files:**
- Modify: `tests/test_motion_sequence.py`
- Test: `tests/test_motion_sequence.py`

- [ ] **Step 1: Update the synchronous `sad` smoke test to expect the expanded mode list**

In `test_single_emotion_runs_synchronously_and_resets_state`, replace the final assertion with:

```python
        self.assertEqual([cmd['mode'] for cmd in controller.commands], [12, 21, 21, 11, 11, 11, 62])
```

- [ ] **Step 2: Add a focused runtime test for the segmented `sad` locomotion commands**

Add this test method to `MotionSequenceTest`:

```python
    def test_sad_sequence_emits_segmented_low_head_walk_commands(self):
        controller = FakeController()
        sequencer = MotionSequence(controller)

        with mock.patch.object(MotionSequence, '_sleep_interruptibly', autospec=True, return_value=None):
            sequencer.execute_emotion('sad')

        locomotion = [cmd for cmd in controller.commands if cmd['mode'] == 11 and cmd['gait_id'] == 27]
        self.assertEqual(len(locomotion), 3)
        self.assertEqual([cmd['duration'] for cmd in locomotion], [450, 450, 400])
        self.assertEqual([cmd['rpy'][1] for cmd in locomotion], [-0.14, -0.12, -0.10])
        self.assertEqual([cmd['velocity'][0] for cmd in locomotion], [-0.04, -0.04, -0.03])
        self.assertTrue(all(cmd['body_height'] == 0.19 for cmd in locomotion))
        self.assertEqual(controller.commands[-1]['mode'], 62)
        self.assertEqual(controller.commands[-1]['gait_id'], 3)
```

- [ ] **Step 3: Run the focused runtime test to verify it fails before the config change**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_motion_sequence.py::MotionSequenceTest::test_sad_sequence_emits_segmented_low_head_walk_commands"
```

Expected: FAIL because the active `sad` config still emits one locomotion command instead of the required three-command burst.

- [ ] **Step 4: Commit the red runtime test**

```bash
git add tests/test_motion_sequence.py
git commit -m "test: cover sad segmented low-head walk"
```

### Task 3: Replace the single long walk with segmented low-head locomotion

**Files:**
- Modify: `config_fixed.py`
- Test: `tests/test_emotion_contract.py`
- Test: `tests/test_motion_sequence.py`

- [ ] **Step 1: Replace the current single `sad` locomotion block with three short low-head walk steps**

In `config_fixed.py`, replace this block:

```python
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.05, 0.0, 0.0],
                'rpy': [0.0, -0.12, 0.0],
                'step_height': [0.02, 0.02],
                'body_height': 0.19,
                'duration': 2000,
            },
```

with these three blocks:

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

- [ ] **Step 2: Run the focused contract and runtime tests to verify the new segmented walk passes**

Run:
```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_emotion_contract.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_motion_sequence.py::MotionSequenceTest::test_sad_sequence_emits_segmented_low_head_walk_commands" \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_motion_sequence.py::MotionSequenceTest::test_single_emotion_runs_synchronously_and_resets_state"
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
git commit -m "feat: segment sad low-head walk"
```

### Task 4: Real-robot verification pass

**Files:**
- Modify: none
- Test: `config_fixed.py`

- [ ] **Step 1: Run the `sad` emotion on the robot**

Run:
```bash
python3 /home/grazier/cyberdog_ws/Emotion_dog/main.py sad
```

Expected observable behavior:
- the robot lowers its body
- the robot pauses in a visible head-down pose
- the robot performs a short backward slow walk while keeping a visible sad pitch
- the robot executes the sit action at the end

- [ ] **Step 2: If the robot still recenters too quickly, adjust only the three locomotion step values and re-run the focused tests before another robot pass**

Use only these allowed tuning directions:

```python
# Allowed tuning knobs inside the three mode=11 sad steps only:
# - velocity[0] within [-0.05, -0.02]
# - rpy[1] within [-0.16, -0.08]
# - duration per step within [300, 600]
```

After each tuning pass, run:

```bash
PYTHONPATH="/home/grazier/cyberdog_ws/Emotion_dog:/home/grazier/cyberdog_ws/Emotion_dog/tests" python3 -m pytest -q \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_emotion_contract.py" \
  "/home/grazier/cyberdog_ws/Emotion_dog/tests/test_motion_sequence.py"
```

Expected: PASS before the next real-robot run.

- [ ] **Step 3: Commit the final tuned values after the robot pass**

```bash
git add config_fixed.py tests/test_emotion_contract.py tests/test_motion_sequence.py
git commit -m "tune: stabilize sad low-head walk"
```
