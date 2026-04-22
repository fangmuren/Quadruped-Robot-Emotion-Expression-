# Emotion_dog Real-Robot Safety Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `Emotion_dog` into a safer, more diagnosable real-robot control program that prefers safe lie-down on stop/error and is closer to running correctly on hardware.

**Architecture:** Keep the existing `main.py` → `motion_sequence.py` → `robot_control.py` layering, but move safety/runtime correctness into the control layer and make the sequence layer result-aware. Entrypoints stop delegating raw shutdown to `close()` and instead drive a unified stop → safe lie-down → close lifecycle with clear logs.

**Tech Stack:** Python 3, LCM, existing `unittest` test suite, standard output logging.

---

## File map

- Modify: `Emotion_dog/robot_control.py`
  - Add structured logging helpers, feedback timestamp tracking, fatal/non-fatal state, action result helpers, safe lie-down/shutdown methods, and command execution modes.
- Modify: `Emotion_dog/motion_sequence.py`
  - Switch from fire-and-sleep sequencing to result-aware execution using the controller’s safe APIs.
- Modify: `Emotion_dog/main.py`
  - Unify top-level lifecycle around stop + safe lie-down + close.
- Modify: `Emotion_dog/demo.py`
  - Apply the same safe lifecycle and fail-fast demo behavior.
- Modify: `Emotion_dog/emotion.py`
  - Tighten config validation for required numeric/vector shapes used by the safer runtime.
- Modify: `Emotion_dog/tests/test_robot_control.py`
  - Add controller tests for feedback freshness, safe lie-down, shutdown path, and timeout/failure behavior.
- Modify: `Emotion_dog/tests/test_motion_sequence.py`
  - Add tests for result-aware step execution, failure short-circuiting, and safe-stop delegation.
- Modify: `Emotion_dog/tests/test_main_runtime.py`
  - Add tests for Ctrl+C/error lifecycle using `shutdown_with_safe_lie_down()`.
- Modify: `Emotion_dog/tests/test_demo_runtime.py`
  - Add demo fail-fast and safe shutdown tests.
- Modify: `Emotion_dog/tests/test_config_validation.py`
  - Add validation tests for malformed step payloads that the safer runtime depends on.

## Implementation notes

- Keep existing config structure (`type`, `sequence`, `stop_motion`, `demo_seconds`) intact.
- Do not touch `Emotion_dog/scripts/auto_lcm_init.sh`.
- Prefer additive changes over large file splits in this round.
- Use standard output logs with stable prefixes: `[INFO]`, `[STEP]`, `[WAIT]`, `[WARN]`, `[ERROR]`, `[SAFE]`.
- Treat “no feedback within timeout” and “action timeout” as fatal runtime failures.
- Default safe exit action is lie-down (`mode=7`, `gait_id=1`).

### Task 1: Lock controller behavior with tests

**Files:**
- Modify: `Emotion_dog/tests/test_robot_control.py`
- Test: `Emotion_dog/tests/test_robot_control.py`

- [ ] **Step 1: Write failing tests for safe shutdown, feedback freshness, and safe lie-down**

Append these tests to `Emotion_dog/tests/test_robot_control.py`:

```python
class SafeShutdownBehaviorTest(unittest.TestCase):
    def make_controller(self):
        controller = CyberDogController.__new__(CyberDogController)
        controller.lcm_tx = FakeLCM()
        controller.life_count = 0
        controller._latest_cmd = None
        controller._tx_lock = FakeLock()
        controller.running = True
        controller.response = None
        controller._last_feedback_at = None
        controller._fatal_error = None
        controller._safe_stop_requested = False
        controller.safe_lie_down = mock.Mock(return_value=True)
        controller.subscription = object()
        controller.lcm_rx = mock.Mock()
        controller.rx_thread = mock.Mock()
        controller.tx_thread = mock.Mock()
        controller.log = mock.Mock()
        return controller

    def test_has_fresh_feedback_requires_recent_timestamp(self):
        controller = self.make_controller()
        controller._last_feedback_at = 100.0

        with mock.patch('robot_control.time.time', return_value=100.2):
            self.assertTrue(controller.has_fresh_feedback(timeout=0.5))
        with mock.patch('robot_control.time.time', return_value=100.8):
            self.assertFalse(controller.has_fresh_feedback(timeout=0.5))

    def test_shutdown_with_safe_lie_down_requests_safe_stop_before_close(self):
        controller = self.make_controller()

        result = controller.shutdown_with_safe_lie_down(reason='keyboard interrupt')

        self.assertTrue(result)
        self.assertTrue(controller._safe_stop_requested)
        controller.safe_lie_down.assert_called_once_with(reason='keyboard interrupt')
        controller.lcm_rx.unsubscribe.assert_called_once_with(controller.subscription)
        controller.rx_thread.join.assert_called_once()
        controller.tx_thread.join.assert_called_once()

    def test_safe_lie_down_sends_lie_down_command_and_waits(self):
        controller = self.make_controller()
        controller.send_single_motion = mock.Mock(return_value=True)

        result = CyberDogController.safe_lie_down(controller, reason='fatal timeout')

        self.assertTrue(result)
        controller.send_single_motion.assert_called_once_with(
            mode=7,
            gait_id=1,
            duration=3500,
            timeout=6.0,
            log_label='safe_lie_down',
        )
```

- [ ] **Step 2: Run controller tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_robot_control -v
```

Expected: FAIL with missing methods like `has_fresh_feedback`, `shutdown_with_safe_lie_down`, or `send_single_motion`.

- [ ] **Step 3: Implement minimal controller lifecycle helpers**

Add these methods to `Emotion_dog/robot_control.py` inside `CyberDogController`:

```python
    def log(self, level, message):
        print(f"[{level}] {message}")

    def has_fresh_feedback(self, timeout=0.5):
        last_feedback = self._last_feedback_at
        if last_feedback is None:
            return False
        return (time.time() - last_feedback) <= timeout

    def safe_lie_down(self, reason='requested stop'):
        self.log('SAFE', f'lie down start reason={reason}')
        result = self.send_single_motion(
            mode=7,
            gait_id=1,
            duration=3500,
            timeout=6.0,
            log_label='safe_lie_down',
        )
        if result:
            self.log('SAFE', 'lie down done')
        else:
            self.log('ERROR', 'lie down failed or timed out')
        return result

    def shutdown_with_safe_lie_down(self, reason='shutdown'):
        self._safe_stop_requested = True
        result = self.safe_lie_down(reason=reason)
        self.running = False
        self.lcm_rx.unsubscribe(self.subscription)
        self.rx_thread.join(timeout=0.1)
        self.tx_thread.join(timeout=0.1)
        return result
```

And initialize these fields in `__init__`:

```python
        self._last_feedback_at = None
        self._fatal_error = None
        self._safe_stop_requested = False
```

- [ ] **Step 4: Run controller tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_robot_control -v
```

Expected: PASS for the new shutdown/freshness tests, while older tests remain green.

- [ ] **Step 5: Commit**

```bash
git add tests/test_robot_control.py robot_control.py
git commit -m "test: lock safe controller shutdown behavior"
```

### Task 2: Implement result-aware controller motion APIs

**Files:**
- Modify: `Emotion_dog/robot_control.py`
- Test: `Emotion_dog/tests/test_robot_control.py`

- [ ] **Step 1: Write failing tests for single-motion waits and fatal timeout recording**

Append these tests to `Emotion_dog/tests/test_robot_control.py`:

```python
class ActionExecutionTest(unittest.TestCase):
    def make_controller(self):
        controller = CyberDogController.__new__(CyberDogController)
        controller.lcm_tx = FakeLCM()
        controller.life_count = 0
        controller._latest_cmd = None
        controller._tx_lock = FakeLock()
        controller.response = None
        controller._last_feedback_at = None
        controller._fatal_error = None
        controller._safe_stop_requested = False
        controller.log = mock.Mock()
        controller.send_command = mock.Mock()
        return controller

    def test_send_single_motion_waits_for_matching_completion(self):
        controller = self.make_controller()
        controller.wait_finish = mock.Mock(return_value=True)

        result = CyberDogController.send_single_motion(
            controller,
            mode=12,
            gait_id=0,
            duration=6000,
            timeout=8.0,
            log_label='recovery',
        )

        self.assertTrue(result)
        controller.send_command.assert_called_once_with(mode=12, gait_id=0, duration=6000)
        controller.wait_finish.assert_called_once_with(mode=12, gait_id=0, timeout=8.0)

    def test_send_single_motion_records_fatal_error_when_wait_times_out(self):
        controller = self.make_controller()
        controller.wait_finish = mock.Mock(return_value=False)

        result = CyberDogController.send_single_motion(
            controller,
            mode=62,
            gait_id=4,
            duration=4000,
            timeout=4.5,
            log_label='wag',
        )

        self.assertFalse(result)
        self.assertEqual(controller._fatal_error, 'action timeout: wag')
```

- [ ] **Step 2: Run the targeted controller action tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_robot_control.ActionExecutionTest -v
```

Expected: FAIL because `send_single_motion` does not exist yet.

- [ ] **Step 3: Implement `send_single_motion()` and stronger response tracking**

In `Emotion_dog/robot_control.py`, update `_on_response()` and add `send_single_motion()`:

```python
    def _on_response(self, channel, data):
        try:
            self.response = robot_control_response_lcmt.decode(data)
            self._last_feedback_at = time.time()
        except Exception as e:
            self.log('WARN', f'response decode error: {e}')

    def send_single_motion(self, mode, gait_id=0, duration=0, timeout=5.0, log_label='motion', **kwargs):
        self.log('STEP', f'{log_label} mode={mode} gait={gait_id} duration={duration}')
        self.send_command(mode=mode, gait_id=gait_id, duration=duration, **kwargs)
        self.log('WAIT', f'{log_label} timeout={timeout:.1f}s')
        finished = self.wait_finish(mode=mode, gait_id=gait_id, timeout=timeout)
        if not finished:
            self._fatal_error = f'action timeout: {log_label}'
            self.log('ERROR', f'action timeout, entering safe path label={log_label}')
            return False
        self.log('INFO', f'{log_label} completed')
        return True
```

Also tighten `wait_finish()` to fail fast when feedback is absent too long:

```python
    def wait_finish(self, mode=None, gait_id=None, timeout=10.0, feedback_timeout=0.5):
        start = time.time()
        while (time.time() - start) < timeout:
            if self._safe_stop_requested:
                return False
            if not self.has_fresh_feedback(timeout=feedback_timeout):
                time.sleep(0.05)
                continue
            response = self.response
            if response and response.order_process_bar >= 95:
                mode_matches = mode is None or response.mode == mode
                gait_matches = gait_id is None or response.gait_id == gait_id
                if mode_matches and gait_matches:
                    return True
            time.sleep(0.05)
        return False
```

- [ ] **Step 4: Run the targeted controller tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_robot_control.ActionExecutionTest -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_robot_control.py robot_control.py
git commit -m "feat: add result-aware controller motion APIs"
```

### Task 3: Tighten config validation for safer runtime assumptions

**Files:**
- Modify: `Emotion_dog/emotion.py`
- Modify: `Emotion_dog/tests/test_config_validation.py`
- Test: `Emotion_dog/tests/test_config_validation.py`

- [ ] **Step 1: Write failing validation tests for malformed scalar and vector payloads**

Append these tests to `Emotion_dog/tests/test_config_validation.py`:

```python
    def test_rejects_non_numeric_duration(self):
        config = {
            'type': 'single',
            'demo_seconds': 2.0,
            'sequence': [
                {'mode': 12, 'gait_id': 0, 'duration': 'fast'},
            ],
        }

        with self.assertRaisesRegex(ValueError, 'duration'):
            validate_emotion_config('bad_duration_type', config)

    def test_rejects_non_list_velocity(self):
        config = {
            'type': 'single',
            'demo_seconds': 2.0,
            'sequence': [
                {'mode': 11, 'gait_id': 10, 'velocity': '0.3,0,0', 'duration': 300},
            ],
        }

        with self.assertRaisesRegex(ValueError, 'velocity'):
            validate_emotion_config('bad_velocity_type', config)
```

- [ ] **Step 2: Run config validation tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_config_validation -v
```

Expected: FAIL because the current validation only checks length and does not reject bad types cleanly.

- [ ] **Step 3: Implement stricter validation in `emotion.py`**

Update helpers in `Emotion_dog/emotion.py`:

```python
def _validate_vector(name: str, value, expected_length: int):
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a list of length {expected_length}")
    if len(value) != expected_length:
        raise ValueError(f"{name} must have length {expected_length}")
    for item in value:
        if not isinstance(item, (int, float)):
            raise ValueError(f"{name} must contain only numbers")
```

And tighten duration checks inside `validate_emotion_config()`:

```python
        duration = step.get('duration', 0)
        if not isinstance(duration, (int, float)):
            raise ValueError(f"{step_name}.duration must be numeric")
        if duration < 0:
            raise ValueError(f"{step_name}.duration must be >= 0")
```

- [ ] **Step 4: Run config validation tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_config_validation -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_config_validation.py emotion.py
git commit -m "test: tighten runtime config validation"
```

### Task 4: Make motion sequences result-aware and fail-fast

**Files:**
- Modify: `Emotion_dog/motion_sequence.py`
- Modify: `Emotion_dog/tests/test_motion_sequence.py`
- Test: `Emotion_dog/tests/test_motion_sequence.py`

- [ ] **Step 1: Write failing sequence tests for controller result handling and safe stop**

Replace the `FakeController` in `Emotion_dog/tests/test_motion_sequence.py` with this one and add the new tests:

```python
class FakeController:
    def __init__(self):
        self.commands = []
        self.single_results = []
        self.continuous_results = []
        self.safe_stop_calls = []

    def send_single_motion(self, **kwargs):
        self.commands.append(('single', kwargs.copy()))
        if self.single_results:
            return self.single_results.pop(0)
        return True

    def start_continuous_motion(self, **kwargs):
        self.commands.append(('continuous', kwargs.copy()))
        if self.continuous_results:
            return self.continuous_results.pop(0)
        return True

    def shutdown_with_safe_lie_down(self, reason='shutdown'):
        self.safe_stop_calls.append(reason)
        return True
```

Add these tests:

```python
    def test_single_emotion_stops_and_safe_lies_down_on_first_failed_step(self):
        controller = FakeController()
        controller.single_results = [False]
        sequencer = MotionSequence(controller)

        sequencer.execute_emotion('sad')

        self.assertFalse(sequencer.is_running())
        self.assertEqual(controller.safe_stop_calls, ['step failure: sad'])

    def test_loop_stop_requests_safe_shutdown(self):
        controller = FakeController()
        sequencer = MotionSequence(controller)

        sequencer.execute_emotion('happy')
        time.sleep(0.05)
        sequencer.stop()

        self.assertFalse(sequencer.is_running())
        self.assertTrue(controller.safe_stop_calls)
```

- [ ] **Step 2: Run motion sequence tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_motion_sequence -v
```

Expected: FAIL because `MotionSequence` still calls `send_command()` directly and never calls `shutdown_with_safe_lie_down()`.

- [ ] **Step 3: Implement result-aware execution in `motion_sequence.py`**

Refactor `_execute_step()` and `stop()` in `Emotion_dog/motion_sequence.py` like this:

```python
    def _execute_step(self, step):
        duration = step.get('duration', 0)
        payload = dict(
            mode=step['mode'],
            gait_id=step.get('gait_id', 0),
            velocity=step.get('velocity', [0, 0, 0]),
            step_height=step.get('step_height', [0, 0]),
            body_height=step.get('body_height', 0.20),
            position=step.get('position', [0, 0, 0]),
            rpy=step.get('rpy', [0, 0, 0]),
            duration=duration,
        )

        is_continuous = duration == 0 and step['mode'] == 11
        if is_continuous:
            ok = self.controller.start_continuous_motion(**payload)
        else:
            timeout = max(1.0, (duration / 1000.0) + 1.0)
            ok = self.controller.send_single_motion(timeout=timeout, log_label=f"step:{step['mode']}:{step.get('gait_id', 0)}", **payload)

        if not ok:
            self._stop_requested = True
            self.controller.shutdown_with_safe_lie_down(reason=f'step failure: {self.current_emotion}')
            return False

        if duration > 0:
            self._sleep_interruptibly(duration / 1000.0)
        return True

    def stop(self):
        print('[MotionSequence] 收到停止请求')
        self._stop_requested = True
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=5.0)
        self.controller.shutdown_with_safe_lie_down(reason='sequence stop')
        self.is_executing = False
```

Update `_execute_single()` and `_run_loop_emotion()` to break immediately when `_execute_step()` returns `False`.

- [ ] **Step 4: Run motion sequence tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_motion_sequence -v
```

Expected: PASS, including new failure/stop tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_motion_sequence.py motion_sequence.py
git commit -m "feat: make emotion sequences fail fast on hardware errors"
```

### Task 5: Add continuous-motion controller support and step-level logs

**Files:**
- Modify: `Emotion_dog/robot_control.py`
- Modify: `Emotion_dog/tests/test_robot_control.py`
- Test: `Emotion_dog/tests/test_robot_control.py`

- [ ] **Step 1: Write failing tests for continuous motion startup and command logs**

Append these tests to `Emotion_dog/tests/test_robot_control.py`:

```python
class ContinuousMotionTest(unittest.TestCase):
    def make_controller(self):
        controller = CyberDogController.__new__(CyberDogController)
        controller.send_command = mock.Mock()
        controller.has_fresh_feedback = mock.Mock(return_value=True)
        controller.log = mock.Mock()
        controller._fatal_error = None
        return controller

    def test_start_continuous_motion_logs_and_sends_command(self):
        controller = self.make_controller()

        result = CyberDogController.start_continuous_motion(
            controller,
            mode=11,
            gait_id=10,
            velocity=[0.3, 0.0, 0.0],
            duration=0,
            log_label='loop_walk',
        )

        self.assertTrue(result)
        controller.send_command.assert_called_once_with(
            mode=11,
            gait_id=10,
            velocity=[0.3, 0.0, 0.0],
            duration=0,
        )
        controller.log.assert_any_call('STEP', 'loop_walk mode=11 gait=10 duration=0 continuous=true')
```

- [ ] **Step 2: Run the targeted controller tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_robot_control.ContinuousMotionTest -v
```

Expected: FAIL because `start_continuous_motion()` does not exist yet.

- [ ] **Step 3: Implement `start_continuous_motion()` in `robot_control.py`**

Add this method:

```python
    def start_continuous_motion(self, mode, gait_id=0, duration=0, log_label='continuous', **kwargs):
        self.log('STEP', f'{log_label} mode={mode} gait={gait_id} duration={duration} continuous=true')
        self.send_command(mode=mode, gait_id=gait_id, duration=duration, **kwargs)
        if not self.has_fresh_feedback(timeout=1.0):
            self._fatal_error = f'no feedback while starting continuous motion: {log_label}'
            self.log('ERROR', self._fatal_error)
            return False
        return True
```

Also add an `[INFO] controller started ...` log near the end of `__init__()` and log each `send_command()` call:

```python
        self.log('INFO', f'controller started tx={self.TX_URL} rx={self.RX_URL} cmd={self.CHAN_CMD} resp={self.CHAN_RESP}')
```

```python
        self.log('INFO', f'send_command mode={mode} gait={gait_id} duration={duration}')
```

- [ ] **Step 4: Run the targeted controller tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_robot_control.ContinuousMotionTest -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_robot_control.py robot_control.py
git commit -m "feat: add continuous motion startup checks and logs"
```

### Task 6: Update `main.py` runtime lifecycle to use safe shutdown

**Files:**
- Modify: `Emotion_dog/main.py`
- Modify: `Emotion_dog/tests/test_main_runtime.py`
- Test: `Emotion_dog/tests/test_main_runtime.py`

- [ ] **Step 1: Write failing runtime tests for keyboard interrupt and error shutdown**

Append these tests to `Emotion_dog/tests/test_main_runtime.py`:

```python
class FakeControllerWithSafeShutdown(FakeController):
    def __init__(self):
        super().__init__()
        self.shutdown_calls = []

    def shutdown_with_safe_lie_down(self, reason='shutdown'):
        self.shutdown_calls.append(reason)
        self.closed = True
        return True


class KeyboardInterruptSequencer(FakeSequencer):
    def execute_emotion(self, emotion):
        raise KeyboardInterrupt


class MainSafeShutdownTest(unittest.TestCase):
    def setUp(self):
        FakeSequencer.instances.clear()

    def test_keyboard_interrupt_uses_safe_shutdown(self):
        controller = FakeControllerWithSafeShutdown()

        with mock.patch.object(emotion_main, 'CyberDogController', return_value=controller), \
             mock.patch.object(emotion_main, 'MotionSequence', KeyboardInterruptSequencer), \
             mock.patch.object(sys, 'argv', ['main.py', 'sad']):
            emotion_main.main()

        self.assertEqual(controller.shutdown_calls, ['keyboard interrupt'])
```

- [ ] **Step 2: Run the main runtime tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_main_runtime -v
```

Expected: FAIL because `main.py` still calls `controller.close()` directly.

- [ ] **Step 3: Implement safe shutdown lifecycle in `main.py`**

Update the end of `Emotion_dog/main.py` like this:

```python
    controller = CyberDogController()
    sequencer = MotionSequence(controller)
    shutdown_reason = 'normal exit'

    print(f"[INFO] 执行情绪: {args.emotion}")

    try:
        sequencer.execute_emotion(args.emotion)

        runtime_type, _demo_seconds = get_runtime_policy(args.emotion)
        wait_seconds = get_post_execute_wait_seconds(args.emotion)

        if args.loop and runtime_type == 'loop':
            print('[INFO] 循环模式，按 Ctrl+C 停止')
            while sequencer.is_running():
                time.sleep(0.1)
        elif runtime_type == 'loop' and wait_seconds > 0:
            print(f"[INFO] 演示 {wait_seconds:.1f} 秒后停止...")
            time.sleep(wait_seconds)
            sequencer.stop()
    except KeyboardInterrupt:
        shutdown_reason = 'keyboard interrupt'
        print('[WARN] 被中断，进入安全趴下')
    except Exception as exc:
        shutdown_reason = f'unhandled error: {exc}'
        print(f'[ERROR] {shutdown_reason}')
        raise
    finally:
        controller.shutdown_with_safe_lie_down(reason=shutdown_reason)
        print('[INFO] 程序结束')
```

- [ ] **Step 4: Run main runtime tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_main_runtime -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_main_runtime.py main.py
git commit -m "feat: use safe shutdown lifecycle in main entrypoint"
```

### Task 7: Update demo lifecycle to fail fast and safe-stop

**Files:**
- Modify: `Emotion_dog/demo.py`
- Modify: `Emotion_dog/tests/test_demo_runtime.py`
- Test: `Emotion_dog/tests/test_demo_runtime.py`

- [ ] **Step 1: Write failing demo tests for emotion failure and safe shutdown**

Append these tests to `Emotion_dog/tests/test_demo_runtime.py`:

```python
class FakeController:
    def __init__(self):
        self.shutdown_calls = []

    def shutdown_with_safe_lie_down(self, reason='shutdown'):
        self.shutdown_calls.append(reason)
        return True


class DemoSafeShutdownTest(unittest.TestCase):
    def test_demo_stops_after_first_runtime_error(self):
        controller = FakeController()
        sequencer = mock.Mock()
        sequencer.execute_emotion.side_effect = [None, RuntimeError('step timeout')]

        with mock.patch('demo.CyberDogController', return_value=controller), \
             mock.patch('demo.MotionSequence', return_value=sequencer), \
             mock.patch('demo.SixEmotions.ALL', ['happy', 'sad']), \
             mock.patch('demo.get_emotion_config', side_effect=[{'type': 'single'}, {'type': 'single'}]), \
             mock.patch('demo.get_post_execute_wait_seconds', return_value=0.0):
            with self.assertRaises(RuntimeError):
                demo.demo_all_emotions()

        self.assertEqual(controller.shutdown_calls, ['demo error: step timeout'])
```

- [ ] **Step 2: Run demo runtime tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_demo_runtime -v
```

Expected: FAIL because `demo.py` still calls `close()` directly and does not attach the failure reason.

- [ ] **Step 3: Implement fail-fast safe lifecycle in `demo.py`**

Update `Emotion_dog/demo.py`:

```python
    controller = CyberDogController()
    sequencer = MotionSequence(controller)
    shutdown_reason = 'demo complete'

    try:
        for emotion in SixEmotions.ALL:
            config = get_emotion_config(emotion)
            print(f"[INFO] demo emotion={emotion} type={config['type']}")

            sequencer.execute_emotion(emotion)
            wait_seconds = get_post_execute_wait_seconds(emotion)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            if config['type'] == 'loop':
                sequencer.stop()
                time.sleep(0.5)

            print(f"[INFO] demo emotion complete={emotion}")
    except KeyboardInterrupt:
        shutdown_reason = 'demo keyboard interrupt'
        print('[WARN] 演示被中断，进入安全趴下')
    except Exception as exc:
        shutdown_reason = f'demo error: {exc}'
        print(f'[ERROR] {shutdown_reason}')
        raise
    finally:
        controller.shutdown_with_safe_lie_down(reason=shutdown_reason)
        print('[INFO] 演示结束')
```

- [ ] **Step 4: Run demo runtime tests to verify they pass**

Run:

```bash
python3 -m unittest tests.test_demo_runtime -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_demo_runtime.py demo.py
git commit -m "feat: make demo fail fast with safe lie down"
```

### Task 8: Run focused regression suite and real-robot readiness smoke checks

**Files:**
- Modify: `Emotion_dog/robot_control.py`
- Modify: `Emotion_dog/motion_sequence.py`
- Modify: `Emotion_dog/main.py`
- Modify: `Emotion_dog/demo.py`
- Modify: `Emotion_dog/emotion.py`
- Test: `Emotion_dog/tests/test_robot_control.py`
- Test: `Emotion_dog/tests/test_motion_sequence.py`
- Test: `Emotion_dog/tests/test_main_runtime.py`
- Test: `Emotion_dog/tests/test_demo_runtime.py`
- Test: `Emotion_dog/tests/test_config_validation.py`

- [ ] **Step 1: Run the focused unit test set**

Run:

```bash
python3 -m unittest \
  tests.test_robot_control \
  tests.test_motion_sequence \
  tests.test_main_runtime \
  tests.test_demo_runtime \
  tests.test_config_validation -v
```

Expected: PASS for all five modules.

- [ ] **Step 2: Run the import probe to verify no top-level regressions**

Run:

```bash
python3 -m unittest tests.test_import_probe -v
```

Expected: PASS.

- [ ] **Step 3: Run the CLI list command as a smoke check**

Run:

```bash
python3 main.py --list
```

Expected output includes:

```text
可用情绪:
  - happy
  - sad
  - fearful
  - angry
  - disgusted
  - surprised
```

- [ ] **Step 4: Run the single-emotion runtime smoke test on host only**

Run:

```bash
python3 -m unittest tests.test_main_runtime.MainRuntimeTest -v
```

Expected: PASS, proving the top-level runtime path still works with fake controller/sequencer wiring.

- [ ] **Step 5: Commit**

```bash
git add robot_control.py motion_sequence.py main.py demo.py emotion.py tests/test_robot_control.py tests/test_motion_sequence.py tests/test_main_runtime.py tests/test_demo_runtime.py tests/test_config_validation.py
git commit -m "feat: harden Emotion_dog real-robot runtime lifecycle"
```

## Spec coverage self-check

- Safe lie-down as the default exit behavior: covered by Tasks 1, 2, 4, 6, and 7.
- Runtime correctness for heartbeat, waits, and feedback freshness: covered by Tasks 1, 2, and 5.
- Result-aware sequence execution and fail-fast behavior: covered by Task 4.
- Logging for startup, steps, waits, errors, and safe shutdown: covered by Tasks 2, 5, 6, and 7.
- Config validation and clearer startup failures: covered by Task 3.
- Focused regression and acceptance checks: covered by Task 8.

## Placeholder/type consistency self-check

- No `TODO`, `TBD`, or “implement later” placeholders remain.
- Controller API names are consistent across tasks: `send_single_motion`, `start_continuous_motion`, `safe_lie_down`, `shutdown_with_safe_lie_down`, `has_fresh_feedback`.
- Sequence layer consistently calls `shutdown_with_safe_lie_down(reason=...)` for fatal stop paths.
- Entrypoints consistently call `shutdown_with_safe_lie_down(reason=...)` in `finally`.
