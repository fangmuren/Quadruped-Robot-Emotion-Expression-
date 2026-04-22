import sys
import time
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
            time.sleep(0.001)

        def handle_timeout(self, timeout_ms):
            time.sleep(min(timeout_ms / 1000.0, 0.001))

        def publish(self, *args, **kwargs):
            self.published.append(args)


sys.modules.setdefault('lcm', types.SimpleNamespace(LCM=FakeLCMModule.LCM))

from robot_control import CyberDogController


class FakeLCM:
    def __init__(self):
        self.published = []

    def publish(self, channel, payload):
        self.published.append((channel, payload))


class FakeLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class RobotControlMappingTest(unittest.TestCase):
    def make_controller(self):
        controller = CyberDogController.__new__(CyberDogController)
        controller.lcm_tx = FakeLCM()
        controller.life_count = 0
        controller._latest_cmd = None
        controller._tx_lock = FakeLock()
        return controller

    def test_relative_pose_command_keeps_explicit_zero_position(self):
        controller = self.make_controller()

        msg = controller.send_command(
            mode=21,
            gait_id=0,
            position=[0, 0, 0],
            rpy=[0.0, -0.12, 0.0],
            body_height=0.19,
            duration=500,
        )

        self.assertEqual(list(msg.pos_des), [0, 0, 0])
        self.assertEqual(list(msg.rpy_des), [0.0, -0.12, 0.0])

    def test_absolute_height_command_uses_body_height_on_z_axis(self):
        controller = self.make_controller()

        msg = controller.send_command(
            mode=21,
            gait_id=5,
            position=[0.2, 0.3, 0.4],
            body_height=0.25,
            duration=300,
        )

        self.assertEqual(list(msg.pos_des), [0, 0, 0.25])
        self.assertEqual(list(msg.rpy_des), [0, 0, 0])

    def test_life_count_wraps_before_int8_overflow(self):
        controller = self.make_controller()
        controller.life_count = 127

        msg = controller.send_command(mode=12, gait_id=0, duration=100)

        self.assertEqual(msg.life_count, 1)
        self.assertEqual(controller.life_count, 2)


class RobotControlHeartbeatTest(unittest.TestCase):
    def test_controller_republishes_latest_command_as_heartbeat(self):
        controller = CyberDogController()
        try:
            controller.send_command(mode=12, gait_id=0, duration=100)
            first_count = len(controller.lcm_tx.published)
            time.sleep(0.05)
            second_count = len(controller.lcm_tx.published)
        finally:
            controller.close()

        self.assertGreaterEqual(first_count, 1)
        self.assertGreater(second_count, first_count)


class WaitFinishMatchingTest(unittest.TestCase):
    def test_wait_finish_requires_matching_mode_and_gait(self):
        controller = CyberDogController.__new__(CyberDogController)
        controller.response = types.SimpleNamespace(order_process_bar=100, mode=12, gait_id=0)

        with mock.patch('robot_control.time.sleep', side_effect=lambda *_args, **_kwargs: None), \
             mock.patch('robot_control.time.time', side_effect=[0.0, 0.0, 10.1]):
            result = controller.wait_finish(mode=11, gait_id=10, timeout=10.0)

        self.assertFalse(result)


class ThreadShutdownTest(unittest.TestCase):
    def test_rx_loop_uses_handle_timeout_for_interruptible_shutdown(self):
        class FakeRx:
            def __init__(self):
                self.handle_timeout_calls = []

            def handle_timeout(self, timeout_ms):
                self.handle_timeout_calls.append(timeout_ms)
                controller.running = False

        controller = CyberDogController.__new__(CyberDogController)
        controller.running = True
        controller.lcm_rx = FakeRx()

        controller._rx_loop()

        self.assertEqual(controller.lcm_rx.handle_timeout_calls, [50])


if __name__ == '__main__':
    unittest.main()
