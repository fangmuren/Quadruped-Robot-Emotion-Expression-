import unittest

import bootstrap  # noqa: F401
from selection_strategy import build_behavior_unit, compile_behavior_unit_to_sequence


class BehaviorHierarchyTest(unittest.TestCase):
    def test_behavior_unit_contains_four_macro_phases(self):
        unit = build_behavior_unit('happy', rho=0.5)
        self.assertEqual(
            [phase['name'] for phase in unit['phases']],
            [
                'neutral_initialization',
                'posture_shaping',
                'expressive_movement',
                'reinforcing_or_ending',
            ],
        )

    def test_compile_behavior_unit_to_sequence_returns_runtime_shape(self):
        unit = build_behavior_unit('fearful', rho=0.5)
        config = compile_behavior_unit_to_sequence(unit)
        self.assertTrue({'type', 'demo_seconds', 'sequence'}.issubset(config.keys()))
        self.assertIsInstance(config['sequence'], list)
        self.assertTrue(config['sequence'])
        self.assertTrue(all('mode' in step for step in config['sequence']))


if __name__ == '__main__':
    unittest.main()
