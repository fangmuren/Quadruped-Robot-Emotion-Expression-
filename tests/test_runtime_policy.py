import unittest

import bootstrap  # noqa: F401
from config import EMOTION_CONFIGS
from emotion import get_post_execute_wait_seconds


def get_runtime_policy(emotion):
    config = EMOTION_CONFIGS[emotion]
    return config['type'], config['demo_seconds']


class RuntimePolicyTest(unittest.TestCase):
    def test_runtime_policy_is_configuration_driven(self):
        self.assertEqual(get_runtime_policy('happy'), ('loop', 6.0))
        self.assertEqual(get_runtime_policy('sad'), ('single', 4.0))
        self.assertEqual(get_runtime_policy('surprised'), ('single', 2.0))

    def test_single_emotions_do_not_wait_after_synchronous_execution(self):
        self.assertEqual(get_post_execute_wait_seconds('sad'), 0.0)
        self.assertEqual(get_post_execute_wait_seconds('surprised'), 0.0)

    def test_loop_emotions_wait_long_enough_to_finish_one_full_cycle(self):
        self.assertAlmostEqual(get_post_execute_wait_seconds('happy'), 11.9, places=2)


if __name__ == '__main__':
    unittest.main()
