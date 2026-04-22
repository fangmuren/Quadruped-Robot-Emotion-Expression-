import sys
import types
import unittest
from unittest import mock

import bootstrap  # noqa: F401


class FakeLCMModule:
    class LCM:
        def __init__(self, *args, **kwargs):
            self.published = []

        def subscribe(self, *args, **kwargs):
            return object()

        def unsubscribe(self, *args, **kwargs):
            pass

        def handle(self):
            pass

        def handle_timeout(self, timeout_ms):
            return timeout_ms

        def publish(self, *args, **kwargs):
            self.published.append(args)


sys.modules.setdefault('lcm', types.SimpleNamespace(LCM=FakeLCMModule.LCM))

import main as emotion_main


class FakeController:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeSequencer:
    instances = []

    def __init__(self, controller):
        self.controller = controller
        self.executed = []
        self.stop_calls = 0
        FakeSequencer.instances.append(self)

    def execute_emotion(self, emotion):
        self.executed.append(emotion)

    def is_running(self):
        return False

    def stop(self):
        self.stop_calls += 1


class MainRuntimeTest(unittest.TestCase):
    def setUp(self):
        FakeSequencer.instances.clear()

    def test_single_emotion_does_not_sleep_after_execution(self):
        sleep_calls = []

        with mock.patch.object(emotion_main, 'CyberDogController', FakeController), \
             mock.patch.object(emotion_main, 'MotionSequence', FakeSequencer), \
             mock.patch.object(emotion_main.time, 'sleep', side_effect=lambda seconds: sleep_calls.append(seconds)), \
             mock.patch.object(sys, 'argv', ['main.py', 'sad']):
            emotion_main.main()

        self.assertEqual(len(FakeSequencer.instances), 1)
        self.assertEqual(FakeSequencer.instances[0].executed, ['sad'])
        self.assertEqual(sleep_calls, [])
        self.assertEqual(FakeSequencer.instances[0].stop_calls, 0)

    def test_loop_emotion_waits_for_effective_runtime_then_stops(self):
        sleep_calls = []

        with mock.patch.object(emotion_main, 'CyberDogController', FakeController), \
             mock.patch.object(emotion_main, 'MotionSequence', FakeSequencer), \
             mock.patch.object(emotion_main.time, 'sleep', side_effect=lambda seconds: sleep_calls.append(seconds)), \
             mock.patch.object(sys, 'argv', ['main.py', 'happy']):
            emotion_main.main()

        self.assertEqual(len(FakeSequencer.instances), 1)
        self.assertEqual(FakeSequencer.instances[0].executed, ['happy'])
        self.assertEqual(sleep_calls, [11.9])
        self.assertEqual(FakeSequencer.instances[0].stop_calls, 1)


if __name__ == '__main__':
    unittest.main()
