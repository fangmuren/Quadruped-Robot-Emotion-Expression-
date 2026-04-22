import unittest

import bootstrap  # noqa: F401
from emotion import validate_emotion_config


class ConfigValidationTest(unittest.TestCase):
    def test_accepts_well_formed_single_emotion_config(self):
        config = {
            'type': 'single',
            'demo_seconds': 2.0,
            'sequence': [
                {'mode': 21, 'gait_id': 5, 'body_height': 0.22, 'duration': 300},
                {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [0.0, 0.1, 0.2], 'duration': 500},
            ],
        }

        validate_emotion_config('sample', config)

    def test_rejects_invalid_step_height_shape(self):
        config = {
            'type': 'single',
            'demo_seconds': 2.0,
            'sequence': [
                {'mode': 11, 'gait_id': 10, 'step_height': [0.04], 'duration': 300},
            ],
        }

        with self.assertRaisesRegex(ValueError, 'step_height'):
            validate_emotion_config('bad_step_height', config)

    def test_rejects_negative_duration(self):
        config = {
            'type': 'single',
            'demo_seconds': 2.0,
            'sequence': [
                {'mode': 12, 'gait_id': 0, 'duration': -1},
            ],
        }

        with self.assertRaisesRegex(ValueError, 'duration'):
            validate_emotion_config('bad_duration', config)


if __name__ == '__main__':
    unittest.main()
