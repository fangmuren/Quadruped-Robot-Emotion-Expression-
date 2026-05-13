#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path

import numpy as np


def load_dataset(path: Path):
    dataset = np.load(path, allow_pickle=True)
    return {
        'X_3d': dataset['X_3d'].astype(np.float32),
        'sample_ids': dataset['sample_ids'],
        'channels': dataset['channels'],
        'phase': dataset['phase'].astype(np.float32),
        'dt_ms': dataset['dt_ms'].astype(np.int32),
        'n_frames': dataset['n_frames'].astype(np.int32),
    }


def build_gaussian_basis(phase, n_basis):
    if n_basis <= 0:
        raise ValueError('n_basis 必须大于 0')

    centers = np.linspace(0.0, 1.0, n_basis, dtype=np.float32)
    if n_basis == 1:
        width = np.float32(1.0)
    else:
        width = np.float32(centers[1] - centers[0])
        if width <= 0:
            width = np.float32(1.0)

    basis = np.exp(-0.5 * ((phase[:, None] - centers[None, :]) / width) ** 2).astype(np.float32)
    return basis, centers, width


def fit_sample_weights(basis, sample_matrix):
    weights = []
    for channel_idx in range(sample_matrix.shape[1]):
        channel_weights, _, _, _ = np.linalg.lstsq(basis, sample_matrix[:, channel_idx], rcond=None)
        weights.append(channel_weights.astype(np.float32))
    return np.concatenate(weights, axis=0).astype(np.float32)


def fit_promp(dataset, n_basis):
    x_3d = dataset['X_3d']
    phase = dataset['phase']
    channels = dataset['channels']
    basis, centers, width = build_gaussian_basis(phase, n_basis)

    sample_weights = np.stack(
        [fit_sample_weights(basis, sample_matrix) for sample_matrix in x_3d],
        axis=0,
    ).astype(np.float32)

    mu_w = sample_weights.mean(axis=0).astype(np.float32)
    if sample_weights.shape[0] > 1:
        sigma_w = np.cov(sample_weights, rowvar=False).astype(np.float32)
    else:
        sigma_w = np.zeros((sample_weights.shape[1], sample_weights.shape[1]), dtype=np.float32)

    return {
        'phase': phase.astype(np.float32),
        'channels': channels,
        'basis_centers': centers.astype(np.float32),
        'basis_width': np.asarray([width], dtype=np.float32),
        'mu_w': mu_w,
        'Sigma_w': sigma_w,
        'n_basis': np.asarray([n_basis], dtype=np.int32),
        'n_samples': np.asarray([x_3d.shape[0]], dtype=np.int32),
        'n_channels': np.asarray([x_3d.shape[2]], dtype=np.int32),
        'n_frames': dataset['n_frames'].astype(np.int32),
        'dt_ms': dataset['dt_ms'].astype(np.int32),
        'sample_ids': dataset['sample_ids'],
    }


def save_model(path: Path, model):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **model)


def fit_dataset_file(dataset_path: Path, output_path: Path, n_basis=8):
    dataset = load_dataset(Path(dataset_path))
    model = fit_promp(dataset, n_basis=n_basis)
    save_model(Path(output_path), model)
    return model


def default_output_path(input_path: Path, output_path):
    if output_path is not None:
        return Path(output_path)
    stem = input_path.stem
    return input_path.parent / f'{stem}_promp.npz'


def main():
    parser = argparse.ArgumentParser(description='从 happy 训练矩阵拟合最小 ProMP 模型')
    parser.add_argument('input_npz', help='输入矩阵 npz 文件，例如 data/happy_promp/matrix/happy_low.npz')
    parser.add_argument('--output', default=None, help='输出模型文件路径')
    parser.add_argument('--n-basis', type=int, default=8, help='高斯基函数数量')
    args = parser.parse_args()

    input_path = Path(args.input_npz)
    output_path = default_output_path(input_path, args.output)
    model = fit_dataset_file(input_path, output_path, n_basis=args.n_basis)

    print(f'[DONE] input={input_path}')
    print(f'[DONE] output={output_path}')
    print(f'[DONE] n_samples={int(model["n_samples"][0])}')
    print(f'[DONE] n_basis={int(model["n_basis"][0])}')


if __name__ == '__main__':
    main()
