import time
import unittest
from unittest import mock

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

        with mock.patch.object(MotionSequence, '_sleep_interruptibly', autospec=True, return_value=None):
            sequencer.execute_emotion('sad')

        self.assertFalse(sequencer.is_running())
        self.assertEqual(sequencer.current_emotion, 'sad')
        self.assertEqual([cmd['mode'] for cmd in controller.commands], [12, 21, 21, 21, 11, 62])

    def test_sad_sequence_emits_confirmed_pitch_and_height_tuning(self):
        controller = FakeController()
        sequencer = MotionSequence(controller)

        with mock.patch.object(MotionSequence, '_sleep_interruptibly', autospec=True, return_value=None):
            sequencer.execute_emotion('sad')

        self.assertEqual(len(controller.commands), 6)
        self.assertEqual(controller.commands[1]['body_height'], 0.19)
        self.assertEqual(controller.commands[2]['rpy'][1], -0.20)
        self.assertEqual(controller.commands[2]['duration'], 1500)
        self.assertEqual(controller.commands[3]['body_height'], 0.235)
        self.assertEqual(controller.commands[4]['mode'], 11)
        self.assertEqual(controller.commands[4]['gait_id'], 27)
        self.assertEqual(controller.commands[4]['velocity'][0], -0.04)
        self.assertEqual(controller.commands[4]['rpy'][1], 0.20)
        self.assertEqual(controller.commands[4]['body_height'], 0.235)
        self.assertEqual(controller.commands[4]['duration'], 3000)
        self.assertEqual(controller.commands[5]['mode'], 62)
        self.assertEqual(controller.commands[5]['gait_id'], 3)
        self.assertEqual(controller.commands[5]['duration'], 3000)

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

    def test_happy_sequence_contains_2500ms_nodding_trot_burst(self):
        original_happy = EMOTION_CONFIGS['happy']
        EMOTION_CONFIGS['happy'] = {
            'type': 'single',
            'demo_seconds': 2.5,
            'sequence': [
                {'mode': 11, 'gait_id': 10, 'velocity': [0.40, 0.0, 0.0], 'step_height': [0.04, 0.04], 'body_height': 0.24, 'rpy': [0.0, -0.10, 0.0], 'duration': 250},
                {'mode': 11, 'gait_id': 10, 'velocity': [0.40, 0.0, 0.0], 'step_height': [0.04, 0.04], 'body_height': 0.24, 'rpy': [0.0, -0.04, 0.0], 'duration': 250},
                {'mode': 11, 'gait_id': 10, 'velocity': [0.40, 0.0, 0.0], 'step_height': [0.04, 0.04], 'body_height': 0.24, 'rpy': [0.0, 0.02, 0.0], 'duration': 250},
                {'mode': 11, 'gait_id': 10, 'velocity': [0.40, 0.0, 0.0], 'step_height': [0.04, 0.04], 'body_height': 0.24, 'rpy': [0.0, 0.08, 0.0], 'duration': 250},
                {'mode': 11, 'gait_id': 10, 'velocity': [0.40, 0.0, 0.0], 'step_height': [0.04, 0.04], 'body_height': 0.24, 'rpy': [0.0, 0.12, 0.0], 'duration': 250},
                {'mode': 11, 'gait_id': 10, 'velocity': [0.40, 0.0, 0.0], 'step_height': [0.04, 0.04], 'body_height': 0.24, 'rpy': [0.0, 0.06, 0.0], 'duration': 250},
                {'mode': 11, 'gait_id': 10, 'velocity': [0.40, 0.0, 0.0], 'step_height': [0.04, 0.04], 'body_height': 0.24, 'rpy': [0.0, 0.00, 0.0], 'duration': 250},
                {'mode': 11, 'gait_id': 10, 'velocity': [0.40, 0.0, 0.0], 'step_height': [0.04, 0.04], 'body_height': 0.24, 'rpy': [0.0, -0.05, 0.0], 'duration': 250},
                {'mode': 11, 'gait_id': 10, 'velocity': [0.40, 0.0, 0.0], 'step_height': [0.04, 0.04], 'body_height': 0.24, 'rpy': [0.0, -0.10, 0.0], 'duration': 250},
                {'mode': 11, 'gait_id': 10, 'velocity': [0.40, 0.0, 0.0], 'step_height': [0.04, 0.04], 'body_height': 0.24, 'rpy': [0.0, -0.02, 0.0], 'duration': 250},
            ],
        }
        controller = FakeController()
        sequencer = MotionSequence(controller)

        try:
            with mock.patch.object(MotionSequence, '_sleep_interruptibly', autospec=True, return_value=None):
                sequencer.execute_emotion('happy')
        finally:
            EMOTION_CONFIGS['happy'] = original_happy

        locomotion = [cmd for cmd in controller.commands if cmd['mode'] == 11 and cmd['gait_id'] == 10]
        self.assertEqual(len(locomotion), 10)
        self.assertEqual([cmd['duration'] for cmd in locomotion], [250] * 10)
        self.assertEqual(
            [cmd['rpy'][1] for cmd in locomotion],
            [-0.10, -0.04, 0.02, 0.08, 0.12, 0.06, 0.00, -0.05, -0.10, -0.02],
        )


if __name__ == '__main__':
    unittest.main()
