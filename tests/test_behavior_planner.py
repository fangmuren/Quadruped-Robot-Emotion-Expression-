import unittest

import bootstrap  # noqa: F401
from affective_state import rollout_affective_episode
from bcp_mapping import trajectory_to_bcp_envelopes
from behavior_planner import (
    compile_behavior_plan_to_sequence,
    generate_phase_candidates,
    score_primitive_candidate,
    select_behavior_plan,
)


class BehaviorPlannerTest(unittest.TestCase):
    def test_select_behavior_plan_reports_phase_candidates_with_expected_shape(self):
        envelope = {
            'phase': 'expressive_peak',
            'directionality': {'preferred': 'neutral'},
            'posture_height': {'preferred': 'high'},
            'body_attitude': {'preferred': 'stiff'},
            'motion_speed': {'preferred': 'low'},
            'rhythm': {'preferred': 'punctuated'},
        }

        plan = select_behavior_plan('angry', [envelope], beam_width=2)
        report = plan['rejected_candidates'][0]
        winner = report['phase_candidates'][0]
        loser = report['rejections'][0]

        self.assertEqual(report['selected_primitive'], winner['primitive'])
        self.assertTrue(winner['selected'])
        self.assertIsNone(winner['lost_to'])
        self.assertEqual(0.0, winner['score_gap'])
        self.assertEqual(report['selected_score'], winner['score'])
        self.assertIs(report['selected_candidate'], winner['candidate'])
        self.assertIs(winner['candidate_labels'], winner['candidate']['labels'])
        self.assertFalse(loser['selected'])
        self.assertEqual(report['selected_primitive'], loser['lost_to'])
        self.assertGreaterEqual(loser['score_gap'], 0.0)
        self.assertIs(loser['candidate_labels'], loser['candidate']['labels'])

    def test_generate_phase_candidates_returns_primitive_options(self):
        episode = rollout_affective_episode('fearful', rho=0.8)
        envelopes = trajectory_to_bcp_envelopes('fearful', episode)
        peak_envelope = next(envelope for envelope in envelopes if envelope['phase'] == 'expressive_peak')

        candidates = generate_phase_candidates('fearful', peak_envelope)

        self.assertGreaterEqual(len(candidates), 2)
        self.assertTrue(all('primitive' in candidate for candidate in candidates))
        self.assertTrue(any(candidate['primitive'] == 'freeze' for candidate in candidates))

    def test_generate_phase_candidates_requires_meaningful_envelope_match(self):
        envelope = {
            'phase': 'neutral_hold',
            'directionality': {'preferred': 'neutral'},
            'posture_height': {'preferred': 'medium'},
            'body_attitude': {'preferred': 'steady'},
            'motion_speed': {'preferred': 'low'},
            'rhythm': {'preferred': 'settling'},
        }

        candidates = generate_phase_candidates('fearful', envelope)

        self.assertEqual('recovery_stand', candidates[0]['primitive'])
        self.assertNotIn('freeze', [candidate['primitive'] for candidate in candidates])
        self.assertNotIn('orient', [candidate['primitive'] for candidate in candidates])
        self.assertNotIn('raise_body', [candidate['primitive'] for candidate in candidates])
        self.assertTrue(all(candidate['match_score'] >= 2 for candidate in candidates))

    def test_public_helpers_raise_clear_error_for_unsupported_emotion(self):
        envelope = {
            'phase': 'neutral_hold',
            'directionality': {'preferred': 'neutral'},
            'posture_height': {'preferred': 'medium'},
            'body_attitude': {'preferred': 'steady'},
            'motion_speed': {'preferred': 'low'},
            'rhythm': {'preferred': 'settling'},
        }
        candidate = {
            'primitive': 'recovery_stand',
            'labels': {
                'directionality': 'neutral',
                'posture_height': 'medium',
                'body_attitude': 'steady',
                'motion_speed': 'low',
                'rhythm': 'settling',
            },
            'recovery_tags': {'stability', 'posture'},
        }

        with self.assertRaisesRegex(ValueError, 'Unsupported emotion'):
            generate_phase_candidates('curious', envelope)

        with self.assertRaisesRegex(ValueError, 'Unsupported emotion'):
            score_primitive_candidate('curious', envelope, candidate)

        with self.assertRaisesRegex(ValueError, 'Unsupported emotion'):
            select_behavior_plan('curious', [envelope])

    def test_emotion_signal_changes_close_call_scoring_and_selection(self):
        envelope = {
            'phase': 'expressive_peak',
            'directionality': {'preferred': 'neutral'},
            'posture_height': {'preferred': 'high'},
            'body_attitude': {'preferred': 'stiff'},
            'motion_speed': {'preferred': 'low'},
            'rhythm': {'preferred': 'punctuated'},
        }

        candidates = generate_phase_candidates('angry', envelope)
        candidate_by_primitive = {candidate['primitive']: candidate for candidate in candidates}

        self.assertIn('raise_body', candidate_by_primitive)
        self.assertIn('stiffen', candidate_by_primitive)
        self.assertEqual(
            candidate_by_primitive['raise_body']['phase_bias'],
            candidate_by_primitive['stiffen']['phase_bias'],
        )
        self.assertGreater(
            candidate_by_primitive['stiffen']['emotion_signal_bonus'],
            candidate_by_primitive['raise_body']['emotion_signal_bonus'],
        )

        raise_body_score = score_primitive_candidate('angry', envelope, candidate_by_primitive['raise_body'])
        stiffen_score = score_primitive_candidate('angry', envelope, candidate_by_primitive['stiffen'])

        self.assertEqual('stiffen', candidates[0]['primitive'])
        self.assertEqual(raise_body_score['phase_bias'], stiffen_score['phase_bias'])
        self.assertEqual(raise_body_score['confusion_penalty'], stiffen_score['confusion_penalty'])
        self.assertEqual(raise_body_score['temporal_bonus'], stiffen_score['temporal_bonus'])
        self.assertGreater(stiffen_score['match_score'], raise_body_score['match_score'])
        self.assertGreater(stiffen_score['emotion_signal_component'], raise_body_score['emotion_signal_component'])
        self.assertGreater(stiffen_score['score'], raise_body_score['score'])
        self.assertAlmostEqual(
            stiffen_score['score'] - raise_body_score['score'],
            (
                stiffen_score['match_score']
                - raise_body_score['match_score']
                + stiffen_score['emotion_signal_component']
                - raise_body_score['emotion_signal_component']
            ),
        )

        plan = select_behavior_plan('angry', [envelope], beam_width=2)

        self.assertEqual('stiffen', plan['selected_primitives'][0]['primitive'])
        self.assertEqual('stiffen', plan['confusion_margins'][0]['selected_primitive'])
        self.assertGreater(plan['confusion_margins'][0]['margin'], 0.0)

        first_rejected = plan['rejected_candidates'][0]['rejections'][0]
        self.assertEqual('raise_body', first_rejected['primitive'])
        self.assertGreater(first_rejected['emotion_signal_bonus'], 0.0)
        self.assertEqual(first_rejected['lost_to'], 'stiffen')

    def test_more_confusable_candidate_scores_lower(self):
        episode = rollout_affective_episode('happy', rho=0.8)
        envelopes = trajectory_to_bcp_envelopes('happy', episode)
        ramp_envelope = next(envelope for envelope in envelopes if envelope['phase'] == 'ramp_up')

        less_confusable = {
            'primitive': 'advance',
            'labels': {
                'directionality': 'approach',
                'posture_height': 'high',
                'body_attitude': 'open',
                'motion_speed': 'medium',
                'rhythm': 'buoyant',
            },
            'recovery_tags': {'locomotion'},
        }
        more_confusable = {
            'primitive': 'retreat',
            'labels': {
                'directionality': 'retreat',
                'posture_height': 'low',
                'body_attitude': 'tense',
                'motion_speed': 'medium',
                'rhythm': 'freeze',
            },
            'recovery_tags': {'locomotion'},
        }

        less_score = score_primitive_candidate('happy', ramp_envelope, less_confusable)
        more_score = score_primitive_candidate('happy', ramp_envelope, more_confusable)

        self.assertGreater(less_score['score'], more_score['score'])
        self.assertLess(less_score['confusion_penalty'], more_score['confusion_penalty'])

    def test_compile_behavior_plan_to_sequence_translates_primitives_to_runtime_steps(self):
        primitive_plan = {
            'selected_primitives': [
                {'primitive': 'orient'},
                {'primitive': 'freeze'},
            ]
        }

        compiled = compile_behavior_plan_to_sequence('fearful', primitive_plan)

        self.assertEqual('single', compiled['type'])
        self.assertEqual(2, len(compiled['sequence']))
        self.assertEqual(21, compiled['sequence'][0]['mode'])
        self.assertEqual(12, compiled['sequence'][1]['mode'])
        self.assertGreaterEqual(compiled['demo_seconds'], 1.5)

    def test_compile_behavior_plan_to_sequence_rejects_unknown_primitives(self):
        primitive_plan = {'selected_primitives': [{'primitive': 'unknown_primitive'}]}

        with self.assertRaisesRegex(ValueError, 'Unsupported primitive in behavior plan'):
            compile_behavior_plan_to_sequence('happy', primitive_plan)

    def test_select_behavior_plan_returns_one_selection_and_margin_per_phase(self):
        episode = rollout_affective_episode('fearful', rho=0.8)
        envelopes = trajectory_to_bcp_envelopes('fearful', episode)

        plan = select_behavior_plan('fearful', envelopes, lambda_weight=1.25, beam_width=2)

        self.assertEqual(len(plan['selected_primitives']), len(envelopes))
        self.assertEqual(len(plan['confusion_margins']), len(envelopes))
        self.assertEqual(len(plan['rejected_candidates']), len(envelopes))
        self.assertTrue(all('primitive' in step for step in plan['selected_primitives']))
        self.assertTrue(all('margin' in margin for margin in plan['confusion_margins']))
        self.assertTrue(all(isinstance(rejected, dict) for rejected in plan['rejected_candidates']))
        self.assertTrue(all('phase' in rejected for rejected in plan['rejected_candidates']))
        self.assertTrue(all('selected_primitive' in rejected for rejected in plan['rejected_candidates']))
        self.assertTrue(all('rejections' in rejected for rejected in plan['rejected_candidates']))
        self.assertTrue(
            all('match_score' in rejected['rejections'][0] for rejected in plan['rejected_candidates'] if rejected['rejections'])
        )
        self.assertTrue(
            all(
                'component_scores' in rejected['rejections'][0]
                for rejected in plan['rejected_candidates']
                if rejected['rejections']
            )
        )
        self.assertTrue(all('phase_candidates' in rejected for rejected in plan['rejected_candidates']))
        self.assertTrue(all('beam_winner' in rejected for rejected in plan['rejected_candidates']))
        self.assertTrue(all(rejected['beam_winner'] == rejected['selected_primitive'] for rejected in plan['rejected_candidates']))
        self.assertTrue(all(isinstance(rejected['phase_candidates'], list) for rejected in plan['rejected_candidates']))
        self.assertTrue(all(isinstance(rejected['rejections'], list) for rejected in plan['rejected_candidates']))
        self.assertTrue(
            all(rejected['phase_candidates'][0]['primitive'] == rejected['selected_primitive'] for rejected in plan['rejected_candidates'])
        )
        self.assertTrue(
            all(rejected['phase_candidates'][0]['selected'] for rejected in plan['rejected_candidates'])
        )
        self.assertTrue(
            all(not candidate['selected'] for rejected in plan['rejected_candidates'] for candidate in rejected['rejections'])
        )
        self.assertTrue(
            all(len(rejected['phase_candidates']) == len(rejected['rejections']) + 1 for rejected in plan['rejected_candidates'])
        )
        self.assertTrue(
            all(rejected['rejections'] == rejected['phase_candidates'][1:] for rejected in plan['rejected_candidates'])
        )
        self.assertTrue(
            all(rejected['phase_candidates'][0]['lost_to'] is None for rejected in plan['rejected_candidates'])
        )
        self.assertTrue(
            all(rejected['phase_candidates'][0]['score_gap'] == 0.0 for rejected in plan['rejected_candidates'])
        )
        self.assertTrue(
            all(rejected['phase_candidates'][0]['candidate'] is rejected['selected_candidate'] for rejected in plan['rejected_candidates'])
        )
        self.assertTrue(
            all(rejected['phase_candidates'][0]['candidate_labels'] is rejected['selected_candidate']['labels'] for rejected in plan['rejected_candidates'])
        )
        self.assertTrue(all('selected_candidate' in rejected for rejected in plan['rejected_candidates']))
        self.assertTrue(all('selected_score' in rejected for rejected in plan['rejected_candidates']))
        self.assertTrue(
            all(rejected['selected_score'] == rejected['phase_candidates'][0]['score'] for rejected in plan['rejected_candidates'])
        )
        self.assertTrue(
            all(rejected['selected_candidate']['primitive'] == rejected['selected_primitive'] for rejected in plan['rejected_candidates'])
        )
        self.assertTrue(
            all(rejected['phase_candidates'][0]['emotion'] == 'fearful' for rejected in plan['rejected_candidates'])
        )

    def test_rejected_candidates_include_score_breakdown_details(self):
        episode = rollout_affective_episode('fearful', rho=0.8)
        envelopes = trajectory_to_bcp_envelopes('fearful', episode)

        plan = select_behavior_plan('fearful', envelopes, lambda_weight=1.25, beam_width=2)

        first_rejected = next(
            rejected['rejections'][0]
            for rejected in plan['rejected_candidates']
            if rejected['rejections']
        )

        self.assertIn('primitive', first_rejected)
        self.assertIn('score', first_rejected)
        self.assertIn('match_score', first_rejected)
        self.assertIn('phase_bias', first_rejected)
        self.assertIn('temporal_bonus', first_rejected)
        self.assertIn('emotion_signal_bonus', first_rejected)
        self.assertIn('emotion_signal_component', first_rejected)
        self.assertIn('confusion_penalty', first_rejected)
        self.assertIn('component_scores', first_rejected)
        self.assertEqual(
            {
                'match_score',
                'phase_bias',
                'temporal_bonus',
                'emotion_signal_bonus',
                'emotion_signal_component',
                'confusion_penalty',
            },
            set(first_rejected['component_scores']),
        )
        self.assertEqual(
            first_rejected['component_scores']['emotion_signal_bonus'],
            first_rejected['emotion_signal_bonus'],
        )
        self.assertEqual(
            first_rejected['component_scores']['emotion_signal_component'],
            first_rejected['emotion_signal_component'],
        )
        self.assertEqual(
            first_rejected['component_scores']['match_score'],
            first_rejected['match_score'],
        )
        self.assertEqual(
            first_rejected['component_scores']['confusion_penalty'],
            first_rejected['confusion_penalty'],
        )
        self.assertIn('lost_to', first_rejected)
        self.assertIn('score_gap', first_rejected)
        self.assertGreaterEqual(first_rejected['score_gap'], 0.0)
        self.assertIn('phase', first_rejected)
        self.assertIn('emotion', first_rejected)
        self.assertIn('candidate_labels', first_rejected)
        self.assertIn('candidate', first_rejected)
        self.assertIs(first_rejected['candidate_labels'], first_rejected['candidate']['labels'])
        self.assertNotEqual(first_rejected['primitive'], first_rejected['lost_to'])
        self.assertGreaterEqual(first_rejected['score_gap'], 0.0)
        self.assertLessEqual(
            first_rejected['score'],
            first_rejected['score'] + first_rejected['score_gap'],
        )

    def test_selected_branch_margin_matches_that_branch_candidate_score(self):
        envelopes = [
            {
                'phase': 'neutral_hold',
                'directionality': {'preferred': 'orient'},
                'posture_height': {'preferred': 'medium'},
                'body_attitude': {'preferred': 'alert'},
                'motion_speed': {'preferred': 'medium'},
                'rhythm': {'preferred': 'punctuated'},
            },
            {
                'phase': 'expressive_peak',
                'directionality': {'preferred': 'retreat'},
                'posture_height': {'preferred': 'low'},
                'body_attitude': {'preferred': 'tense'},
                'motion_speed': {'preferred': 'medium'},
                'rhythm': {'preferred': 'freeze'},
            },
        ]

        plan = select_behavior_plan('fearful', envelopes, lambda_weight=0.5, beam_width=2)

        selected_candidate = plan['selected_primitives'][1]
        previous_candidate = plan['selected_primitives'][0]
        scored_candidates = [
            score_primitive_candidate(
                'fearful',
                envelopes[1],
                candidate,
                previous_candidate=previous_candidate,
                lambda_weight=0.5,
            )
            for candidate in generate_phase_candidates('fearful', envelopes[1])
        ]
        selected_score = next(item['score'] for item in scored_candidates if item['primitive'] == selected_candidate['primitive'])
        competing_scores = [item['score'] for item in scored_candidates if item['primitive'] != selected_candidate['primitive']]
        expected_margin = selected_score - max(competing_scores)

        self.assertEqual(plan['confusion_margins'][1]['selected_primitive'], selected_candidate['primitive'])
        self.assertAlmostEqual(plan['confusion_margins'][1]['margin'], expected_margin)
        self.assertGreaterEqual(plan['confusion_margins'][1]['margin'], 0.0)

    def test_confusion_penalty_tracks_plausible_competing_behavior(self):
        fearful_envelope = {
            'phase': 'expressive_peak',
            'directionality': {'preferred': 'retreat'},
            'posture_height': {'preferred': 'low'},
            'body_attitude': {'preferred': 'tense'},
            'motion_speed': {'preferred': 'medium'},
            'rhythm': {'preferred': 'freeze'},
        }
        retreat_like = {
            'primitive': 'retreat',
            'labels': {
                'directionality': 'retreat',
                'posture_height': 'low',
                'body_attitude': 'tense',
                'motion_speed': 'medium',
                'rhythm': 'freeze',
            },
            'recovery_tags': {'locomotion'},
        }
        happy_like = {
            'primitive': 'advance',
            'labels': {
                'directionality': 'approach',
                'posture_height': 'high',
                'body_attitude': 'open',
                'motion_speed': 'medium',
                'rhythm': 'buoyant',
            },
            'recovery_tags': {'locomotion'},
        }

        retreat_score = score_primitive_candidate('fearful', fearful_envelope, retreat_like)
        happy_score = score_primitive_candidate('fearful', fearful_envelope, happy_like)

        self.assertGreater(retreat_score['match_score'], happy_score['match_score'])
        self.assertLess(retreat_score['confusion_penalty'], happy_score['confusion_penalty'])
        self.assertGreater(retreat_score['score'], happy_score['score'])


if __name__ == '__main__':
    unittest.main()
