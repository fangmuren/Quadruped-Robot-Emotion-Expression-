import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from analysis_metrics import (
    balanced_accuracy,
    confusion_matrix,
    confusion_pair_rate,
    mean_pad_by_emotion,
    overall_accuracy,
    per_class_accuracy,
)


class AnalysisMetricsTest(unittest.TestCase):
    def test_recognition_metrics_match_expected_rates(self):
        rows = [
            {'emotion': 'happy', 'prediction': 'happy'},
            {'emotion': 'happy', 'prediction': 'surprised'},
            {'emotion': 'sad', 'prediction': 'sad'},
            {'emotion': 'sad', 'prediction': 'fearful'},
        ]

        self.assertEqual(overall_accuracy(rows), 0.5)
        self.assertEqual(per_class_accuracy(rows), {'happy': 0.5, 'sad': 0.5})
        self.assertEqual(balanced_accuracy(rows), 0.5)
        self.assertEqual(confusion_matrix(rows)['happy']['surprised'], 1)
        self.assertEqual(confusion_pair_rate(rows, 'happy', 'surprised'), 0.5)

    def test_metric_helpers_return_zero_like_values_for_empty_or_missing_targets(self):
        self.assertEqual(overall_accuracy([]), 0.0)
        self.assertEqual(per_class_accuracy([]), {})
        self.assertEqual(balanced_accuracy([]), 0.0)
        self.assertEqual(confusion_matrix([]), {})
        self.assertEqual(confusion_pair_rate([], 'happy', 'sad'), 0.0)
        self.assertEqual(confusion_pair_rate([{'emotion': 'sad', 'prediction': 'sad'}], 'happy', 'sad'), 0.0)

    def test_mean_pad_by_emotion_averages_each_dimension(self):
        rows = [
            {'emotion': 'happy', 'pleasure': 6, 'arousal': 5, 'dominance': 4},
            {'emotion': 'happy', 'pleasure': 4, 'arousal': 3, 'dominance': 2},
            {'emotion': 'sad', 'pleasure': 1, 'arousal': 2, 'dominance': 3},
        ]

        self.assertEqual(
            mean_pad_by_emotion(rows),
            {
                'happy': {'pleasure': 5.0, 'arousal': 4.0, 'dominance': 3.0},
                'sad': {'pleasure': 1.0, 'arousal': 2.0, 'dominance': 3.0},
            },
        )


if __name__ == '__main__':
    unittest.main()
