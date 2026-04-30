import unittest

import bootstrap  # noqa: F401
from emotion import SixEmotions, get_all_emotions, get_emotion_config


class EmotionContractTest(unittest.TestCase):
    def test_exports_exactly_six_pdf_emotions(self):
        self.assertEqual(
            get_all_emotions(),
            ['happy', 'sad', 'fearful', 'angry', 'disgusted', 'surprised'],
        )
        self.assertEqual(SixEmotions.ALL, get_all_emotions())

    def test_removed_emotions_are_not_available(self):
        with self.assertRaises(ValueError):
            get_emotion_config('confused')
        with self.assertRaises(ValueError):
            get_emotion_config('lost')

    def test_every_emotion_has_runtime_metadata(self):
        expected = {
            'happy': ('loop', 6.0),
            'sad': ('single', 4.0),
            'fearful': ('single', 4.0),
            'angry': ('single', 3.0),
            'disgusted': ('single', 3.0),
            'surprised': ('single', 2.0),
        }
        for emotion, pair in expected.items():
            config = get_emotion_config(emotion)
            self.assertEqual((config['type'], config['demo_seconds']), pair)

    def test_pdf_sequences_match_expected_signature(self):
        expected = {
            'happy': {
                'type': 'loop',
                'modes': [12, 21, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 62],
                'gaits': [0, 5, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 4],
                'stop_mode': 3,
            },
            'sad': {
                'type': 'single',
                'modes': [12, 21, 21, 21, 11, 62],
                'gaits': [0, 5, 0, 5, 27, 3],
            },
            'fearful': {
                'type': 'single',
                'modes': [21, 21, 11, 21, 21, 21],
                'gaits': [5, 0, 27, 0, 0, 0],
            },
            'angry': {
                'type': 'single',
                'modes': [12, 21, 21, 11, 21, 21, 3],
                'gaits': [0, 5, 0, 10, 0, 0, 0],
            },
            'disgusted': {
                'type': 'single',
                'modes': [21, 21, 21, 21, 21, 21],
                'gaits': [5, 0, 0, 0, 0, 0],
            },
            'surprised': {
                'type': 'single',
                'modes': [21, 21, 21, 3],
                'gaits': [5, 0, 0, 0],
            },
        }

        for emotion, spec in expected.items():
            config = get_emotion_config(emotion)
            self.assertEqual(config['type'], spec['type'])
            self.assertEqual([step['mode'] for step in config['sequence']], spec['modes'])
            self.assertEqual([step.get('gait_id', 0) for step in config['sequence']], spec['gaits'])
            if emotion == 'happy':
                locomotion_steps = config['sequence'][2:12]
                self.assertEqual([step['duration'] for step in locomotion_steps], [250] * 10)
                self.assertEqual(sum(step['duration'] for step in locomotion_steps), 2500)
                self.assertEqual(
                    [step['rpy'][1] for step in locomotion_steps],
                    [-0.10, -0.04, 0.02, 0.08, 0.12, 0.06, 0.00, -0.05, -0.10, -0.02],
                )
            if emotion == 'sad':
                sequence = config['sequence']
                self.assertEqual(sequence[1]['body_height'], 0.19)
                self.assertEqual(sequence[2]['rpy'][1], -0.20)
                self.assertEqual(sequence[2]['duration'], 1500)
                self.assertEqual(sequence[3]['body_height'], 0.235)
                self.assertEqual(sequence[4]['velocity'][0], -0.04)
                self.assertEqual(sequence[4]['rpy'][1], 0.20)
                self.assertEqual(sequence[4]['body_height'], 0.235)
                self.assertEqual(sequence[4]['duration'], 3000)
                self.assertEqual(sequence[5]['duration'], 3000)
            if 'stop_mode' in spec:
                self.assertEqual(config['stop_motion']['mode'], spec['stop_mode'])


if __name__ == '__main__':
    unittest.main()
