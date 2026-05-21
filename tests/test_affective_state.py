import unittest

import bootstrap  # noqa: F401
from affective_state import (
    EPISODE_PHASES,
    NEUTRAL_PAD,
    PAD_ANCHORS,
    compute_target_state,
    rollout_affective_episode,
    update_affective_state,
)


class AffectiveStateTest(unittest.TestCase):
    def test_compute_target_state_interpolates_between_neutral_and_anchor(self):
        neutral = compute_target_state('happy', 0.0)
        strong = compute_target_state('happy', 1.0)
        mid = compute_target_state('happy', 0.5)

        self.assertEqual(neutral, NEUTRAL_PAD)
        self.assertEqual(strong, PAD_ANCHORS['happy'])
        self.assertEqual(
            mid,
            [
                (NEUTRAL_PAD[i] + PAD_ANCHORS['happy'][i]) / 2.0
                for i in range(3)
            ],
        )

    def test_update_affective_state_moves_toward_target(self):
        start = [0.0, 0.0, 0.0]
        target = [0.6, 0.8, 0.2]

        updated = update_affective_state(start, target, dt=0.5, kappa=1.0)

        self.assertGreater(updated[0], start[0])
        self.assertGreater(updated[1], start[1])
        self.assertGreater(updated[2], start[2])
        self.assertLess(updated[0], target[0])
        self.assertLess(updated[1], target[1])
        self.assertLess(updated[2], target[2])

    def test_update_affective_state_clamps_smoothing_alpha(self):
        start = [0.1, -0.2, 0.3]
        target = [0.6, 0.4, -0.1]

        updated = update_affective_state(start, target, dt=2.0, kappa=1.0)

        for actual, expected in zip(updated, target):
            self.assertAlmostEqual(actual, expected)

    def test_rollout_uses_five_macro_phases(self):
        episode = rollout_affective_episode('happy', rho=0.8)

        self.assertEqual(episode['emotion'], 'happy')
        self.assertEqual(episode['rho'], 0.8)
        self.assertEqual(len(episode['phases']), 5)
        self.assertEqual(
            [phase['name'] for phase in episode['phases']],
            [phase['name'] for phase in EPISODE_PHASES],
        )
        self.assertEqual(
            [phase['target'] for phase in EPISODE_PHASES],
            ['neutral', 'emotion_target', 'emotion_target', 'mid_decay', 'neutral'],
        )
        self.assertEqual(episode['trajectory'][0]['phase'], 'neutral_hold')
        self.assertEqual(episode['trajectory'][-1]['phase'], 'return_to_neutral')
        self.assertIn('ramp_up', [point['phase'] for point in episode['trajectory']])

        for phase in episode['phases']:
            self.assertIn('name', phase)
            self.assertIn('kappa', phase)
            self.assertIn('target', phase)
            self.assertIn('states', phase)
            self.assertIsInstance(phase['states'], list)
            self.assertGreaterEqual(len(phase['states']), 1)
            for point in phase['states']:
                self.assertEqual(point['phase'], phase['name'])
                self.assertIn('state', point)

        self.assertEqual(episode['phases'][0]['states'][0]['state'], NEUTRAL_PAD)
        self.assertEqual(
            episode['phases'][-1]['states'][-1]['state'],
            episode['trajectory'][-1]['state'],
        )

    def test_rollout_ramp_up_moves_monotonically_toward_target(self):
        episode = rollout_affective_episode('happy', rho=0.7, ramp_steps=4)

        ramp_points = [
            point for point in episode['trajectory']
            if point['phase'] == 'ramp_up'
        ]
        target = episode['target_state']
        previous_distance = None

        self.assertEqual(len(ramp_points), 4)

        for point in ramp_points:
            current_distance = sum(
                abs(target[i] - point['state'][i])
                for i in range(3)
            )
            if previous_distance is not None:
                self.assertLessEqual(current_distance, previous_distance)
            previous_distance = current_distance

    def test_rollout_decay_moves_away_from_peak_toward_neutral(self):
        episode = rollout_affective_episode('happy', rho=0.9, dt=0.5, ramp_steps=4)
        peak_state = episode['phases'][2]['states'][-1]['state']
        decay_points = episode['phases'][3]['states']

        self.assertGreaterEqual(len(decay_points), 2)

        peak_distance = sum(abs(value) for value in peak_state)
        final_decay_distance = sum(abs(value) for value in decay_points[-1]['state'])

        self.assertLess(final_decay_distance, peak_distance)

        previous_distance_from_peak = None
        for point in decay_points:
            current_distance_from_peak = sum(
                abs(point['state'][i] - peak_state[i])
                for i in range(3)
            )
            if previous_distance_from_peak is not None:
                self.assertGreaterEqual(
                    current_distance_from_peak,
                    previous_distance_from_peak,
                )
            previous_distance_from_peak = current_distance_from_peak

    def test_rollout_returns_near_neutral_through_transitions(self):
        episode = rollout_affective_episode('sad', rho=0.9, dt=0.5)
        return_points = episode['phases'][4]['states']
        final_state = return_points[-1]['state']

        self.assertGreaterEqual(len(return_points), 2)

        previous_distance = None
        for point in return_points:
            current_distance = sum(abs(value) for value in point['state'])
            if previous_distance is not None:
                self.assertLessEqual(current_distance, previous_distance)
            previous_distance = current_distance

        for i, neutral_value in enumerate(NEUTRAL_PAD):
            self.assertAlmostEqual(final_state[i], neutral_value, delta=0.05)

    def test_rollout_phases_chain_continuously_between_transitions(self):
        episode = rollout_affective_episode('happy', rho=0.8, dt=0.5, ramp_steps=4)

        self.assertEqual(
            episode['phases'][2]['states'][-1]['state'],
            episode['phases'][3]['states'][0]['state'],
        )
        self.assertEqual(
            episode['phases'][3]['states'][-1]['state'],
            episode['phases'][4]['states'][0]['state'],
        )
        self.assertNotEqual(
            episode['phases'][4]['states'][0]['state'],
            episode['phases'][4]['states'][-1]['state'],
        )
        self.assertNotEqual(
            episode['phases'][3]['states'][0]['state'],
            episode['phases'][3]['states'][-1]['state'],
        )

        final_state = episode['phases'][4]['states'][-1]['state']
        for i, neutral_value in enumerate(NEUTRAL_PAD):
            self.assertAlmostEqual(final_state[i], neutral_value, delta=0.05)

    def test_rollout_ends_near_neutral(self):
        episode = rollout_affective_episode('sad', rho=0.9, dt=0.5)
        final_state = episode['trajectory'][-1]['state']

        for i, neutral_value in enumerate(NEUTRAL_PAD):
            self.assertAlmostEqual(final_state[i], neutral_value, delta=0.05)

        self.assertEqual(
            final_state,
            episode['phases'][-1]['states'][-1]['state'],
        )


if __name__ == '__main__':
    unittest.main()
