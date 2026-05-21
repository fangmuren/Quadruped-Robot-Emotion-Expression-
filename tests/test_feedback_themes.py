import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from feedback_themes import detect_feedback_themes, summarize_feedback_themes


class FeedbackThemesTest(unittest.TestCase):
    def test_detect_feedback_themes_returns_matching_cue_buckets(self):
        text = '它先后退又停住不动，身体也压低了，看起来像害怕。'

        self.assertEqual(
            detect_feedback_themes(text),
            {'directionality', 'rhythm_flow', 'posture_height'},
        )

    def test_summarize_feedback_themes_counts_each_detected_theme_once_per_row(self):
        rows = [
            {'text': '它冲过来，动作很快。'},
            {'text': '它后退然后停住。'},
        ]

        self.assertEqual(
            summarize_feedback_themes(rows),
            {
                'directionality': 2,
                'posture_height': 0,
                'body_attitude': 0,
                'motion_speed': 1,
                'motion_energy': 0,
                'rhythm_flow': 1,
            },
        )

    def test_detect_feedback_themes_does_not_treat_common_connectors_as_rhythm_signal(self):
        self.assertEqual(detect_feedback_themes('它后退然后看着你。'), {'directionality'})


if __name__ == '__main__':
    unittest.main()
