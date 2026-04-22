"""
动作序列执行器
执行情绪动作序列
"""

import threading
import time
from config import EMOTION_CONFIGS


class MotionSequence:
    """执行情绪动作序列"""

    def __init__(self, controller):
        self.controller = controller
        self.current_emotion = None
        self.is_executing = False
        self._stop_requested = False
        self._worker = None

    def execute_emotion(self, emotion: str):
        if emotion not in EMOTION_CONFIGS:
            raise ValueError(f"Unknown emotion: {emotion}")
        if self.is_running():
            raise RuntimeError("Another emotion is already running")

        config = EMOTION_CONFIGS[emotion]
        self.current_emotion = emotion
        self._stop_requested = False
        self.is_executing = True

        print(f"[MotionSequence] 开始执行情绪: {emotion} (类型: {config['type']})")

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
                    print(f"[MotionSequence] 循环执行: mode={step['mode']}, gait_id={step.get('gait_id', 0)}")
                    self._execute_step(step)

            if stop_motion:
                print(f"[MotionSequence] 执行停止动作: {stop_motion}")
                self._execute_step(stop_motion)
        finally:
            self.is_executing = False
            self._worker = None

    def _execute_single(self, sequence):
        for i, step in enumerate(sequence):
            if self._stop_requested:
                break
            print(f"[MotionSequence] 执行步骤 {i+1}/{len(sequence)}: mode={step['mode']}, gait_id={step.get('gait_id', 0)}")
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
            self._sleep_interruptibly(duration / 1000.0)

    def _sleep_interruptibly(self, seconds):
        deadline = time.time() + seconds
        while not self._stop_requested:
            remaining = deadline - time.time()
            if remaining <= 0:
                return
            time.sleep(min(0.05, remaining))

    def stop(self):
        print("[MotionSequence] 收到停止请求")
        self._stop_requested = True
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=5.0)
        if worker is None:
            self.is_executing = False

    def is_running(self):
        return self.is_executing
