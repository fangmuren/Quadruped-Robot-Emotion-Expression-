import copy
import unittest

import bootstrap  # noqa: F401
from affective_state import rollout_affective_episode
from bcp_mapping import EMOTION_PHASE_PROTOTYPES, state_to_bcp, trajectory_to_bcp_envelopes


class BcpMappingTest(unittest.TestCase):
    def test_trajectory_to_bcp_envelopes_returns_one_envelope_per_phase(self):
        episode = rollout_affective_episode('fearful', rho=0.8)
        envelopes = trajectory_to_bcp_envelopes('fearful', episode)

        self.assertEqual(
            [envelope['phase'] for envelope in envelopes],
            ['neutral_hold', 'ramp_up', 'expressive_peak', 'decay', 'return_to_neutral'],
        )
        self.assertTrue(all('source_states' in envelope for envelope in envelopes))
        self.assertTrue(
            all(
                {
                    'directionality',
                    'posture_height',
                    'body_attitude',
                    'motion_speed',
                    'motion_energy',
                    'rhythm',
                }.issubset(envelope)
                for envelope in envelopes
            )
        )

    def test_trajectory_to_bcp_envelopes_includes_energy_bounds_and_preserves_phase_states(self):
        episode = rollout_affective_episode('happy', rho=0.8)
        envelopes = trajectory_to_bcp_envelopes('happy', episode)

        for envelope, phase in zip(envelopes, episode['phases']):
            self.assertEqual(set(envelope['motion_energy']), {'lower', 'upper'})
            self.assertEqual(envelope['source_states'], [point['state'] for point in phase['states']])

    def test_trajectory_to_bcp_envelopes_rejects_missing_phase_with_clear_error(self):
        episode = rollout_affective_episode('happy', rho=0.8)
        broken_episode = copy.deepcopy(episode)
        broken_episode['phases'] = [
            phase for phase in broken_episode['phases'] if phase['name'] != 'decay'
        ]

        with self.assertRaisesRegex(ValueError, 'missing required phase: decay'):
            trajectory_to_bcp_envelopes('happy', broken_episode)

    def test_state_to_bcp_respects_emotion_specific_phase_directionality(self):
        phase_state = (0.4, 0.75, 0.1)

        happy_bcp = state_to_bcp('happy', phase_state)
        disgusted_bcp = state_to_bcp('disgusted', phase_state)

        self.assertEqual(happy_bcp['directionality'], 'approach')
        self.assertEqual(disgusted_bcp['directionality'], 'avoid')

    def test_all_emotion_prototypes_cover_all_phases(self):
        for emotion, prototypes in EMOTION_PHASE_PROTOTYPES.items():
            self.assertEqual(
                set(prototypes),
                {'neutral_hold', 'ramp_up', 'expressive_peak', 'decay', 'return_to_neutral'},
                msg=emotion,
            )
            self.assertTrue(
                all('motion_energy' in prototype for prototype in prototypes.values()),
                msg=emotion,
            )
            self.assertTrue(
                all(len(prototype['motion_energy']) == 2 for prototype in prototypes.values()),
                msg=emotion,
            )

    def test_trajectory_to_bcp_envelopes_rejects_malformed_phase_states(self):
        episode = rollout_affective_episode('sad', rho=0.8)
        broken_episode = copy.deepcopy(episode)
        broken_episode['phases'][0]['states'] = [{'not_state': (0.0, 0.0, 0.0)}]

        with self.assertRaisesRegex(ValueError, 'phase neutral_hold has malformed states'):
            trajectory_to_bcp_envelopes('sad', broken_episode)

    def test_fearful_peak_envelope_prefers_freeze_or_retreat_behavior(self):
        episode = rollout_affective_episode('fearful', rho=0.8)
        envelopes = trajectory_to_bcp_envelopes('fearful', episode)
        peak = next(envelope for envelope in envelopes if envelope['phase'] == 'expressive_peak')

        self.assertIn(peak['directionality']['preferred'], {'orient', 'retreat'})
        self.assertEqual(peak['rhythm']['preferred'], 'freeze')

    def test_happy_return_to_neutral_lowers_energy_vs_peak(self):
        episode = rollout_affective_episode('happy', rho=0.8)
        envelopes = trajectory_to_bcp_envelopes('happy', episode)
        peak = next(envelope for envelope in envelopes if envelope['phase'] == 'expressive_peak')
        ending = next(envelope for envelope in envelopes if envelope['phase'] == 'return_to_neutral')

        self.assertGreater(peak['motion_energy']['upper'], ending['motion_energy']['upper'])


if __name__ == '__main__':
    unittest.main()
