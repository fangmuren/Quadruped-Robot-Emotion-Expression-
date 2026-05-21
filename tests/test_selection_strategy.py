import unittest

import bootstrap  # noqa: F401
import affective_state
import bcp_mapping
import selection_strategy
from selection_strategy import build_behavior_plan, build_emotion_configs


class SelectionStrategyTest(unittest.TestCase):
    def test_build_behavior_plan_returns_intermediate_layers(self):
        plan = build_behavior_plan('happy', rho=0.7, lambda_weight=1.1)

        self.assertEqual(plan['emotion'], 'happy')
        self.assertEqual(plan['rho'], 0.7)
        self.assertIn('target_state', plan)
        self.assertIn('trajectory', plan)
        self.assertIn('phases', plan)
        self.assertIn('bcp_envelopes', plan)
        self.assertIn('selected_primitives', plan)
        self.assertIn('confusion_margins', plan)
        self.assertIn('rejected_candidates', plan)
        self.assertIn('compiled_config', plan)

    def test_build_emotion_configs_still_returns_runtime_ready_shape(self):
        configs = build_emotion_configs(rho=0.6, lambda_weight=1.0)
        happy = configs['happy']

        self.assertIn('type', happy)
        self.assertIn('demo_seconds', happy)
        self.assertIn('sequence', happy)
        self.assertTrue(happy['sequence'])
        self.assertTrue(all('mode' in step for step in happy['sequence']))

    def test_facade_reexports_canonical_affective_helpers(self):
        self.assertIs(selection_strategy.NEUTRAL_PAD, affective_state.NEUTRAL_PAD)
        self.assertIs(selection_strategy.PAD_ANCHORS, affective_state.PAD_ANCHORS)
        self.assertIs(selection_strategy.compute_target_state, affective_state.compute_target_state)
        self.assertIs(selection_strategy.update_affective_state, affective_state.update_affective_state)
        self.assertIs(selection_strategy.state_to_bcp, bcp_mapping.state_to_bcp)

    def test_build_emotion_configs_ignores_top_k_for_compatibility(self):
        configs_top_1 = build_emotion_configs(top_k=1, rho=0.6, lambda_weight=1.0)
        configs_top_3 = build_emotion_configs(top_k=3, rho=0.6, lambda_weight=1.0)
        self.assertEqual(configs_top_1, configs_top_3)


if __name__ == '__main__':
    unittest.main()
