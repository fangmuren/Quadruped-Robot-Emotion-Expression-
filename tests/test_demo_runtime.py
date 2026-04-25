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

import demo as emotion_demo


class FakeController:
    instances = []

    def __init__(self):
        self.closed = False
        FakeController.instances.append(self)

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

    def stop(self):
        self.stop_calls += 1


class DemoRuntimeTest(unittest.TestCase):
    def setUp(self):
        FakeController.instances.clear()
        FakeSequencer.instances.clear()

    def test_demo_waits_only_for_loop_emotions_using_effective_runtime(self):
        sleep_calls = []

        with mock.patch.object(emotion_demo, 'CyberDogController', FakeController), \
             mock.patch.object(emotion_demo, 'MotionSequence', FakeSequencer), \
             mock.patch.object(emotion_demo.time, 'sleep', side_effect=lambda seconds: sleep_calls.append(seconds)), \
             mock.patch.object(emotion_demo.SixEmotions, 'ALL', ['sad', 'happy']):
            emotion_demo.demo_all_emotions()

        self.assertEqual(len(FakeSequencer.instances), 1)
        self.assertEqual(FakeSequencer.instances[0].executed, ['sad', 'happy'])
        self.assertEqual(sleep_calls, [12.9, 0.5])
        self.assertEqual(FakeSequencer.instances[0].stop_calls, 1)
        self.assertTrue(FakeController.instances[0].closed)


if __name__ == '__main__':
    unittest.main()
