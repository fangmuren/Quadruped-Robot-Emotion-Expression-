#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
from pathlib import Path

import numpy as np


def load_model(path: Path):
    model = np.load(path, allow_pickle=True)
    return {
        'phase': model['phase'].astype(np.float32),
        'channels': model['channels'],
        'basis_centers': model['basis_centers'].astype(np.float32),
        'basis_width': float(model['basis_width'][0]),
        'mu_w': model['mu_w'].astype(np.float32),
        'Sigma_w': model['Sigma_w'].astype(np.float32),
        'n_basis': int(model['n_basis'][0]),
        'n_channels': int(model['n_channels'][0]),
        'n_frames': int(model['n_frames'][0]),
        'dt_ms': int(model['dt_ms'][0]),
    }


def build_gaussian_basis(phase, centers, width):
    safe_width = width if width > 0 else 1.0
    return np.exp(-0.5 * ((phase[:, None] - centers[None, :]) / safe_width) ** 2).astype(np.float32)


def sample_weight_vector(model, rng=None):
    sigma = model['Sigma_w']
    mu = model['mu_w']
    if np.allclose(sigma, 0.0):
        return mu.copy()
    generator = rng if rng is not None else np.random.default_rng()
    return generator.multivariate_normal(mu, sigma).astype(np.float32)


def reconstruct_trajectory(model, weight_vector):
    basis = build_gaussian_basis(model['phase'], model['basis_centers'], model['basis_width'])
    n_basis = model['n_basis']
    channels = model['channels'].tolist()

    channel_map = {}
    for channel_idx, channel_name in enumerate(channels):
        start = channel_idx * n_basis
        end = start + n_basis
        channel_weights = weight_vector[start:end]
        channel_values = basis @ channel_weights
        channel_map[channel_name] = [round(float(value), 6) for value in channel_values]
    return channel_map


def sample_trajectory(model, sample_id, emotion, intensity, rng=None):
    weight_vector = sample_weight_vector(model, rng=rng)
    channel_map = reconstruct_trajectory(model, weight_vector)
    phase = [round(float(value), 6) for value in model['phase']]
    time_ms = [model['dt_ms'] * idx for idx in range(model['n_frames'])]

    return {
        'sample_id': sample_id,
        'emotion': emotion,
        'intensity': intensity,
        'dt_ms': model['dt_ms'],
        'n_frames': model['n_frames'],
        'phase': phase,
        'time_ms': time_ms,
        'channels': channel_map,
        'aux_labels': {
            'ornament_type': 'promp_sample',
            'returns_to_neutral': True,
        },
        'meta': {
            'source': 'promp_sample',
            'model_n_basis': model['n_basis'],
        },
    }


def save_traj(path: Path, traj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(traj, f, ensure_ascii=False, indent=2)


def sample_model_file(model_path: Path, output_path: Path, sample_id, emotion='happy', intensity='mid', seed=None):
    model = load_model(Path(model_path))
    rng = np.random.default_rng(seed) if seed is not None else None
    traj = sample_trajectory(model, sample_id=sample_id, emotion=emotion, intensity=intensity, rng=rng)
    save_traj(Path(output_path), traj)
    return traj


def default_output_path(model_path: Path, output_path):
    if output_path is not None:
        return Path(output_path)
    stem = model_path.stem
    return model_path.parent / f'{stem}_sample.traj.json'


def main():
    parser = argparse.ArgumentParser(description='从 happy ProMP 模型采样生成 traj.json')
    parser.add_argument('model_npz', help='输入模型 npz 文件，例如 data/happy_promp/models/happy_mid_promp.npz')
    parser.add_argument('--output', default=None, help='输出 traj.json 路径')
    parser.add_argument('--sample-id', default='happy_sample_001', help='输出样本 ID')
    parser.add_argument('--emotion', default='happy', help='情绪标签')
    parser.add_argument('--intensity', default='mid', help='强度标签')
    parser.add_argument('--seed', type=int, default=None, help='随机种子')
    args = parser.parse_args()

    model_path = Path(args.model_npz)
    output_path = default_output_path(model_path, args.output)
    traj = sample_model_file(
        model_path,
        output_path,
        sample_id=args.sample_id,
        emotion=args.emotion,
        intensity=args.intensity,
        seed=args.seed,
    )

    print(f'[DONE] input={model_path}')
    print(f'[DONE] output={output_path}')
    print(f'[DONE] sample_id={traj["sample_id"]}')
    print(f'[DONE] n_frames={traj["n_frames"]}')


if __name__ == '__main__':
    main()
