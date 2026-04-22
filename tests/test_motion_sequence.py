import time
import unittest

import bootstrap  # noqa: F401
from config import EMOTION_CONFIGS
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
        self.assertEqual([cmd['mode'] for cmd in controller.commands], [12, 21, 21, 11, 62])

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

    def test_stop_interrupts_long_running_loop_step_quickly(self):
        original_happy = EMOTION_CONFIGS['happy']
        EMOTION_CONFIGS['happy'] = {
            'type': 'loop',
            'demo_seconds': 1.0,
            'sequence': [
                {'mode': 12, 'gait_id': 0, 'duration': 1500},
            ],
            'stop_motion': {'mode': 3, 'gait_id': 0, 'duration': 0},
        }
        controller = FakeController()
        sequencer = MotionSequence(controller)

        try:
            sequencer.execute_emotion('happy')
            time.sleep(0.05)
            start = time.time()
            sequencer.stop()
            elapsed = time.time() - start
        finally:
            EMOTION_CONFIGS['happy'] = original_happy

        self.assertLess(elapsed, 0.5)
        self.assertEqual(controller.commands[-1]['mode'], 3)


if __name__ == '__main__':
    unittest.main()
