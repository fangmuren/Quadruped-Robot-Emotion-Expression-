import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'happy_promp'
ANCHOR_TO_TRAJ_PATH = DATA_DIR / 'anchor_to_traj.py'
TRAJ_TO_MATRIX_PATH = DATA_DIR / 'traj_to_matrix.py'
FIT_HAPPY_PROMP_PATH = DATA_DIR / 'fit_happy_promp.py'
SAMPLE_HAPPY_PROMP_PATH = DATA_DIR / 'sample_happy_promp.py'


def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class HappyPrompDataPipelineTest(unittest.TestCase):
    def test_anchor_to_traj_converts_anchor_segments_into_resampled_channels(self):
        module = load_module('anchor_to_traj_module', ANCHOR_TO_TRAJ_PATH)
        anchor = {
            'sample_id': 'happy_low_001',
            'emotion': 'happy',
            'intensity': 'low',
            'source': 'manual_seed',
            'fixed_fields': {
                'mode': 11,
                'gait_id': 27,
                'velocity_y': 0.0,
                'rpy_roll': 0.0,
                'rpy_yaw': 0.0,
                'position': [0.0, 0.0, 0.0],
            },
            'anchors': [
                {
                    'phase': 'enter',
                    'duration_ms': 100,
                    'velocity_x': 0.03,
                    'yaw_rate': 0.00,
                    'step_height_left': 0.020,
                    'step_height_right': 0.020,
                    'body_height': 0.236,
                    'pitch': 0.00,
                    'ornament': 'none',
                },
                {
                    'phase': 'build',
                    'duration_ms': 100,
                    'velocity_x': 0.05,
                    'yaw_rate': 0.10,
                    'step_height_left': 0.024,
                    'step_height_right': 0.024,
                    'body_height': 0.242,
                    'pitch': 0.08,
                    'ornament': 'nod_small',
                },
            ],
            'returns_to_neutral': True,
        }

        traj = module.convert_anchor_to_traj(anchor, dt_ms=50)

        self.assertEqual(traj['sample_id'], 'happy_low_001')
        self.assertEqual(traj['emotion'], 'happy')
        self.assertEqual(traj['intensity'], 'low')
        self.assertEqual(traj['dt_ms'], 50)
        self.assertEqual(traj['n_frames'], 5)
        self.assertEqual(traj['time_ms'], [0, 50, 100, 150, 200])
        self.assertEqual(traj['phase'][0], 0.0)
        self.assertEqual(traj['phase'][-1], 1.0)
        self.assertEqual(traj['aux_labels']['ornament_type'], 'nod_small')
        self.assertEqual(traj['channels']['velocity_x'], [0.03, 0.04, 0.05, 0.05, 0.05])
        self.assertEqual(traj['channels']['yaw_rate'], [0.0, 0.05, 0.1, 0.1, 0.1])
        self.assertEqual(traj['channels']['step_height_left'], [0.02, 0.022, 0.024, 0.024, 0.024])
        self.assertEqual(traj['channels']['body_height'], [0.236, 0.239, 0.242, 0.242, 0.242])
        self.assertEqual(traj['channels']['pitch'], [0.0, 0.04, 0.08, 0.08, 0.08])

    def test_traj_to_matrix_groups_samples_and_exports_expected_shapes(self):
        module = load_module('traj_to_matrix_module', TRAJ_TO_MATRIX_PATH)
        channels = [
            'velocity_x',
            'yaw_rate',
            'step_height_left',
            'step_height_right',
            'body_height',
            'pitch',
        ]

        traj_low = {
            'sample_id': 'happy_low_001',
            'emotion': 'happy',
            'intensity': 'low',
            'dt_ms': 50,
            'n_frames': 3,
            'phase': [0.0, 0.5, 1.0],
            'channels': {
                'velocity_x': [0.03, 0.04, 0.03],
                'yaw_rate': [0.0, 0.05, 0.0],
                'step_height_left': [0.02, 0.022, 0.02],
                'step_height_right': [0.02, 0.022, 0.02],
                'body_height': [0.236, 0.239, 0.236],
                'pitch': [0.0, 0.04, 0.0],
            },
            'aux_labels': {
                'ornament_type': 'nod_small',
                'returns_to_neutral': True,
            },
            'meta': {
                'source': 'manual_seed',
                'total_duration_ms': 100,
            },
        }
        traj_mid = {
            'sample_id': 'happy_mid_001',
            'emotion': 'happy',
            'intensity': 'mid',
            'dt_ms': 50,
            'n_frames': 3,
            'phase': [0.0, 0.5, 1.0],
            'channels': {
                'velocity_x': [0.05, 0.06, 0.05],
                'yaw_rate': [0.0, 0.10, 0.0],
                'step_height_left': [0.024, 0.025, 0.024],
                'step_height_right': [0.024, 0.025, 0.024],
                'body_height': [0.242, 0.245, 0.242],
                'pitch': [0.02, 0.08, 0.02],
            },
            'aux_labels': {
                'ornament_type': 'nod_mid',
                'returns_to_neutral': True,
            },
            'meta': {
                'source': 'manual_seed',
                'total_duration_ms': 100,
            },
        }

        sample_low = module.validate_and_extract(traj_low, channels)
        sample_mid = module.validate_and_extract(traj_mid, channels)
        module.ensure_same_layout([sample_low, sample_mid], channels)
        dataset = module.build_dataset([sample_low, sample_mid], channels)
        groups = module.group_by_intensity([sample_low, sample_mid])

        self.assertEqual(dataset['X_3d'].shape, (2, 3, 6))
        self.assertEqual(dataset['X_flat'].shape, (2, 18))
        self.assertEqual(dataset['sample_ids'].tolist(), ['happy_low_001', 'happy_mid_001'])
        self.assertEqual(dataset['intensities'].tolist(), ['low', 'mid'])
        self.assertEqual(dataset['channels'].tolist(), channels)
        self.assertEqual(dataset['phase'].tolist(), [0.0, 0.5, 1.0])
        self.assertEqual(sorted(groups.keys()), ['low', 'mid'])
        self.assertEqual(len(groups['low']), 1)
        self.assertEqual(len(groups['mid']), 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            module.save_npz(out_dir / 'all_samples.npz', dataset)
            self.assertTrue((out_dir / 'all_samples.npz').exists())

            module.save_metadata_csv(
                out_dir / 'metadata.csv',
                [
                    {
                        'sample_id': sample_low['sample_id'],
                        'emotion': sample_low['emotion'],
                        'intensity': sample_low['intensity'],
                        'dt_ms': sample_low['dt_ms'],
                        'n_frames': sample_low['n_frames'],
                        'ornament_type': sample_low['ornament_type'],
                        'returns_to_neutral': sample_low['returns_to_neutral'],
                        'source': sample_low['source'],
                        'total_duration_ms': sample_low['total_duration_ms'],
                        'file_name': 'happy_low_001.traj.json',
                    }
                ],
            )
            self.assertTrue((out_dir / 'metadata.csv').exists())

    def test_traj_to_matrix_normalizes_mixed_frame_counts_to_target_frames(self):
        module = load_module('traj_to_matrix_module_resample', TRAJ_TO_MATRIX_PATH)
        channels = [
            'velocity_x',
            'yaw_rate',
            'step_height_left',
            'step_height_right',
            'body_height',
            'pitch',
        ]

        traj_low = {
            'sample_id': 'happy_low_001',
            'emotion': 'happy',
            'intensity': 'low',
            'dt_ms': 50,
            'n_frames': 3,
            'phase': [0.0, 0.5, 1.0],
            'channels': {
                'velocity_x': [0.03, 0.04, 0.03],
                'yaw_rate': [0.0, 0.05, 0.0],
                'step_height_left': [0.02, 0.022, 0.02],
                'step_height_right': [0.02, 0.022, 0.02],
                'body_height': [0.236, 0.239, 0.236],
                'pitch': [0.0, 0.04, 0.0],
            },
            'aux_labels': {
                'ornament_type': 'nod_small',
                'returns_to_neutral': True,
            },
            'meta': {
                'source': 'manual_seed',
                'total_duration_ms': 100,
            },
        }
        traj_high = {
            'sample_id': 'happy_high_001',
            'emotion': 'happy',
            'intensity': 'high',
            'dt_ms': 50,
            'n_frames': 5,
            'phase': [0.0, 0.25, 0.5, 0.75, 1.0],
            'channels': {
                'velocity_x': [0.05, 0.07, 0.09, 0.07, 0.05],
                'yaw_rate': [0.0, -0.08, 0.0, 0.08, 0.0],
                'step_height_left': [0.024, 0.027, 0.03, 0.027, 0.024],
                'step_height_right': [0.024, 0.027, 0.03, 0.027, 0.024],
                'body_height': [0.241, 0.248, 0.255, 0.248, 0.241],
                'pitch': [0.03, 0.08, 0.15, 0.08, 0.03],
            },
            'aux_labels': {
                'ornament_type': 'lift',
                'returns_to_neutral': True,
            },
            'meta': {
                'source': 'manual_seed',
                'total_duration_ms': 200,
            },
        }

        sample_low = module.validate_and_extract(traj_low, channels)
        sample_high = module.validate_and_extract(traj_high, channels)
        normalized = module.normalize_samples_to_target_frames([sample_low, sample_high], target_frames=5)
        module.ensure_same_layout(normalized, channels)
        dataset = module.build_dataset(normalized, channels)

        self.assertEqual(dataset['X_3d'].shape, (2, 5, 6))
        self.assertEqual(dataset['X_flat'].shape, (2, 30))
        self.assertEqual(dataset['n_frames'].tolist(), [5])
        self.assertEqual(dataset['phase'].tolist(), [0.0, 0.25, 0.5, 0.75, 1.0])
        self.assertEqual(normalized[0]['sample_id'], 'happy_low_001')
        self.assertEqual(normalized[0]['n_frames'], 5)
        self.assertEqual(normalized[0]['matrix'].shape, (5, 6))
        self.assertAlmostEqual(float(normalized[0]['matrix'][2, 0]), 0.04, places=6)

    def test_fit_happy_promp_fits_matrix_dataset_and_saves_expected_model(self):
        module = load_module('fit_happy_promp_module', FIT_HAPPY_PROMP_PATH)

        phase = [0.0, 0.5, 1.0]
        channels = ['velocity_x', 'pitch']

        x_3d = [
            [
                [0.03, 0.00],
                [0.05, 0.04],
                [0.03, 0.00],
            ],
            [
                [0.04, 0.01],
                [0.06, 0.05],
                [0.04, 0.01],
            ],
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            dataset_path = tmp_path / 'happy_low.npz'
            output_path = tmp_path / 'happy_low_promp.npz'
            np.savez_compressed(
                dataset_path,
                X_3d=np.asarray(x_3d, dtype=np.float32),
                sample_ids=np.asarray(['happy_low_001', 'happy_low_002'], dtype=object),
                emotions=np.asarray(['happy', 'happy'], dtype=object),
                intensities=np.asarray(['low', 'low'], dtype=object),
                ornament_types=np.asarray(['nod_small', 'nod_small'], dtype=object),
                returns_to_neutral=np.asarray([True, True], dtype=bool),
                channels=np.asarray(channels, dtype=object),
                phase=np.asarray(phase, dtype=np.float32),
                dt_ms=np.asarray([50], dtype=np.int32),
                n_frames=np.asarray([3], dtype=np.int32),
            )

            model = module.fit_dataset_file(dataset_path, output_path, n_basis=4)

            self.assertTrue(output_path.exists())
            self.assertEqual(model['phase'].shape, (3,))
            self.assertEqual(model['channels'].tolist(), channels)
            self.assertEqual(model['basis_centers'].shape, (4,))
            self.assertEqual(model['mu_w'].shape, (8,))
            self.assertEqual(model['Sigma_w'].shape, (8, 8))
            self.assertEqual(int(model['n_basis'][0]), 4)
            self.assertEqual(int(model['n_samples'][0]), 2)

            saved = np.load(output_path, allow_pickle=True)
            self.assertEqual(sorted(saved.files), [
                'Sigma_w',
                'basis_centers',
                'basis_width',
                'channels',
                'dt_ms',
                'mu_w',
                'n_basis',
                'n_channels',
                'n_frames',
                'n_samples',
                'phase',
                'sample_ids',
            ])
            self.assertEqual(saved['mu_w'].shape, (8,))
            self.assertEqual(saved['Sigma_w'].shape, (8, 8))

    def test_sample_happy_promp_generates_traj_json_from_model(self):
        module = load_module('sample_happy_promp_module', SAMPLE_HAPPY_PROMP_PATH)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            model_path = tmp_path / 'happy_mid_promp.npz'
            output_path = tmp_path / 'happy_mid_sample_001.traj.json'

            np.savez_compressed(
                model_path,
                phase=np.asarray([0.0, 0.5, 1.0], dtype=np.float32),
                channels=np.asarray(['velocity_x', 'pitch'], dtype=object),
                basis_centers=np.asarray([0.0, 0.5, 1.0], dtype=np.float32),
                basis_width=np.asarray([0.25], dtype=np.float32),
                mu_w=np.asarray([0.03, 0.05, 0.03, 0.00, 0.04, 0.00], dtype=np.float32),
                Sigma_w=np.zeros((6, 6), dtype=np.float32),
                n_basis=np.asarray([3], dtype=np.int32),
                n_channels=np.asarray([2], dtype=np.int32),
                n_frames=np.asarray([3], dtype=np.int32),
                n_samples=np.asarray([1], dtype=np.int32),
                dt_ms=np.asarray([50], dtype=np.int32),
                sample_ids=np.asarray(['happy_mid_001'], dtype=object),
            )

            traj = module.sample_model_file(
                model_path,
                output_path,
                sample_id='happy_mid_sample_001',
                emotion='happy',
                intensity='mid',
            )

            self.assertTrue(output_path.exists())
            basis = np.exp(
                -0.5 * ((np.asarray([0.0, 0.5, 1.0], dtype=np.float32)[:, None] - np.asarray([0.0, 0.5, 1.0], dtype=np.float32)[None, :]) / 0.25) ** 2
            ).astype(np.float32)
            expected_velocity_x = [
                round(float(value), 6)
                for value in basis @ np.asarray([0.03, 0.05, 0.03], dtype=np.float32)
            ]
            expected_pitch = [
                round(float(value), 6)
                for value in basis @ np.asarray([0.00, 0.04, 0.00], dtype=np.float32)
            ]

            self.assertEqual(traj['sample_id'], 'happy_mid_sample_001')
            self.assertEqual(traj['emotion'], 'happy')
            self.assertEqual(traj['intensity'], 'mid')
            self.assertEqual(traj['dt_ms'], 50)
            self.assertEqual(traj['n_frames'], 3)
            self.assertEqual(traj['phase'], [0.0, 0.5, 1.0])
            self.assertEqual(traj['channels']['velocity_x'], expected_velocity_x)
            self.assertEqual(traj['channels']['pitch'], expected_pitch)
            self.assertEqual(traj['aux_labels']['returns_to_neutral'], True)
            self.assertEqual(traj['meta']['source'], 'promp_sample')

            with output_path.open('r', encoding='utf-8') as f:
                saved = json.load(f)
            self.assertEqual(saved['channels']['velocity_x'], expected_velocity_x)
            self.assertEqual(saved['channels']['pitch'], expected_pitch)
            self.assertEqual(saved['time_ms'], [0, 50, 100])
            self.assertEqual(saved['aux_labels']['ornament_type'], 'promp_sample')
            self.assertEqual(saved['meta']['model_n_basis'], 3)
            self.assertEqual(saved['meta']['source'], 'promp_sample')

            saved_model = module.load_model(model_path)
            sampled_weights = module.sample_weight_vector(saved_model)
            self.assertEqual(sampled_weights.shape, (6,))
            self.assertTrue(np.allclose(sampled_weights, np.asarray([0.03, 0.05, 0.03, 0.0, 0.04, 0.0], dtype=np.float32)))

            default_output = module.default_output_path(model_path, None)
            self.assertEqual(default_output.name, 'happy_mid_promp_sample.traj.json')
            self.assertEqual(saved_model['n_basis'], 3)
            self.assertEqual(saved_model['n_channels'], 2)
            self.assertEqual(saved_model['n_frames'], 3)
            self.assertEqual(saved_model['dt_ms'], 50)
            self.assertEqual(saved_model['Sigma_w'].shape, (6, 6))
            self.assertEqual(module.build_gaussian_basis(saved_model['phase'], saved_model['basis_centers'], saved_model['basis_width']).shape, (3, 3))
            self.assertEqual(module.reconstruct_trajectory(saved_model, sampled_weights)['velocity_x'], expected_velocity_x)
            self.assertEqual(module.reconstruct_trajectory(saved_model, sampled_weights)['pitch'], expected_pitch)

            sampled_traj = module.sample_trajectory(saved_model, 'happy_mid_sample_002', 'happy', 'mid')
            self.assertEqual(sampled_traj['sample_id'], 'happy_mid_sample_002')
            self.assertEqual(sampled_traj['channels']['velocity_x'], expected_velocity_x)
            self.assertEqual(sampled_traj['channels']['pitch'], expected_pitch)
            self.assertEqual(sampled_traj['time_ms'], [0, 50, 100])
            self.assertEqual(sampled_traj['meta']['source'], 'promp_sample')
            self.assertEqual(sampled_traj['aux_labels']['returns_to_neutral'], True)

            module.save_traj(tmp_path / 'happy_mid_manual.traj.json', traj)
            self.assertTrue((tmp_path / 'happy_mid_manual.traj.json').exists())
            with (tmp_path / 'happy_mid_manual.traj.json').open('r', encoding='utf-8') as f:
                manual_saved = json.load(f)
            self.assertEqual(manual_saved['channels']['velocity_x'], expected_velocity_x)
            self.assertEqual(manual_saved['channels']['pitch'], expected_pitch)
            self.assertEqual(manual_saved['meta']['source'], 'promp_sample')
            self.assertEqual(manual_saved['aux_labels']['ornament_type'], 'promp_sample')
            self.assertEqual(manual_saved['time_ms'], [0, 50, 100])

            seeded_traj = module.sample_model_file(
                model_path,
                tmp_path / 'happy_mid_sample_003.traj.json',
                sample_id='happy_mid_sample_003',
                emotion='happy',
                intensity='mid',
                seed=123,
            )
            self.assertTrue((tmp_path / 'happy_mid_sample_003.traj.json').exists())
            self.assertEqual(seeded_traj['channels']['velocity_x'], expected_velocity_x)
            self.assertEqual(seeded_traj['channels']['pitch'], expected_pitch)
            self.assertEqual(seeded_traj['meta']['source'], 'promp_sample')
            self.assertEqual(seeded_traj['aux_labels']['returns_to_neutral'], True)
            self.assertEqual(seeded_traj['time_ms'], [0, 50, 100])
            self.assertEqual(seeded_traj['phase'], [0.0, 0.5, 1.0])
            self.assertEqual(seeded_traj['dt_ms'], 50)
            self.assertEqual(seeded_traj['n_frames'], 3)
            self.assertEqual(seeded_traj['emotion'], 'happy')
            self.assertEqual(seeded_traj['intensity'], 'mid')
            self.assertEqual(seeded_traj['meta']['model_n_basis'], 3)
            self.assertEqual(seeded_traj['aux_labels']['ornament_type'], 'promp_sample')
            self.assertEqual(set(seeded_traj['channels'].keys()), {'velocity_x', 'pitch'})
            self.assertTrue(np.allclose(module.sample_weight_vector(saved_model, rng=np.random.default_rng(123)), sampled_weights))
            self.assertEqual(module.default_output_path(model_path, output_path), output_path)
            self.assertEqual(saved_model['channels'].tolist(), ['velocity_x', 'pitch'])
            self.assertEqual(saved_model['phase'].tolist(), [0.0, 0.5, 1.0])
            self.assertEqual(saved_model['basis_centers'].tolist(), [0.0, 0.5, 1.0])
            self.assertTrue(np.allclose(saved_model['mu_w'], np.asarray([0.03, 0.05, 0.03, 0.0, 0.04, 0.0], dtype=np.float32)))
            self.assertEqual(module.reconstruct_trajectory(saved_model, module.sample_weight_vector(saved_model)).keys(), {'velocity_x', 'pitch'})
            self.assertEqual(set(module.sample_trajectory(saved_model, 'happy_mid_sample_005', 'happy', 'mid').keys()), {'sample_id', 'emotion', 'intensity', 'dt_ms', 'n_frames', 'phase', 'time_ms', 'channels', 'aux_labels', 'meta'})
            self.assertEqual(set(module.sample_model_file(model_path, tmp_path / 'happy_mid_sample_005.traj.json', sample_id='happy_mid_sample_005', emotion='happy', intensity='mid').keys()), {'sample_id', 'emotion', 'intensity', 'dt_ms', 'n_frames', 'phase', 'time_ms', 'channels', 'aux_labels', 'meta'})
            self.assertTrue((tmp_path / 'happy_mid_sample_005.traj.json').exists())
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['sample_id'], 'happy_mid_sample_005')
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['channels']['velocity_x'], expected_velocity_x)
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['channels']['pitch'], expected_pitch)
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['meta']['source'], 'promp_sample')
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['aux_labels']['returns_to_neutral'], True)
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['time_ms'], [0, 50, 100])
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['phase'], [0.0, 0.5, 1.0])
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['dt_ms'], 50)
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['n_frames'], 3)
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['emotion'], 'happy')
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['intensity'], 'mid')
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['meta']['model_n_basis'], 3)
            self.assertEqual(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['aux_labels']['ornament_type'], 'promp_sample')
            self.assertEqual(set(json.loads((tmp_path / 'happy_mid_sample_005.traj.json').read_text(encoding='utf-8'))['channels'].keys()), {'velocity_x', 'pitch'})
            self.assertEqual(module.default_output_path(model_path, None), tmp_path / 'happy_mid_promp_sample.traj.json')
            self.assertEqual(module.default_output_path(model_path, output_path), output_path)
            self.assertEqual(module.load_model(model_path)['n_basis'], 3)
            self.assertEqual(module.load_model(model_path)['n_channels'], 2)
            self.assertEqual(module.load_model(model_path)['n_frames'], 3)
            self.assertEqual(module.load_model(model_path)['dt_ms'], 50)
            self.assertEqual(module.build_gaussian_basis(np.asarray([0.0, 0.5, 1.0], dtype=np.float32), np.asarray([0.0, 0.5, 1.0], dtype=np.float32), 0.25).shape, (3, 3))
            self.assertEqual(module.build_gaussian_basis(np.asarray([0.0, 0.5, 1.0], dtype=np.float32), np.asarray([0.0, 0.5, 1.0], dtype=np.float32), 0.25).dtype, np.float32)
            self.assertTrue(np.allclose(module.sample_weight_vector(saved_model), np.asarray([0.03, 0.05, 0.03, 0.0, 0.04, 0.0], dtype=np.float32)))
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['channels']['velocity_x'], expected_velocity_x)
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['channels']['pitch'], expected_pitch)
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['meta']['source'], 'promp_sample')
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['aux_labels']['returns_to_neutral'], True)
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['time_ms'], [0, 50, 100])
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['phase'], [0.0, 0.5, 1.0])
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['dt_ms'], 50)
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['n_frames'], 3)
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['emotion'], 'happy')
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['intensity'], 'mid')
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['meta']['model_n_basis'], 3)
            self.assertEqual(module.sample_trajectory(saved_model, 'happy_mid_sample_006', 'happy', 'mid')['aux_labels']['ornament_type'], 'promp_sample')


if __name__ == '__main__':
    unittest.main()
