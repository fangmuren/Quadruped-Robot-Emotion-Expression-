#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
from pathlib import Path

import numpy as np


DEFAULT_CHANNELS = [
    'velocity_x',
    'yaw_rate',
    'step_height_left',
    'step_height_right',
    'body_height',
    'pitch',
]


def load_json(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def save_metadata_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        'sample_id',
        'emotion',
        'intensity',
        'dt_ms',
        'n_frames',
        'ornament_type',
        'returns_to_neutral',
        'source',
        'total_duration_ms',
        'file_name',
    ]
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def list_traj_files(input_dir: Path):
    files = sorted(input_dir.glob('*.traj.json'))
    if not files:
        raise FileNotFoundError(f'未找到 .traj.json 文件: {input_dir}')
    return files


def validate_and_extract(traj, channels):
    required_top = ['sample_id', 'emotion', 'intensity', 'dt_ms', 'n_frames', 'phase', 'channels']
    for key in required_top:
        if key not in traj:
            raise ValueError(f'traj.json 缺少字段: {key}')

    traj_channels = traj['channels']
    for ch in channels:
        if ch not in traj_channels:
            raise ValueError(f'traj.json 缺少通道: {ch}')

    n_frames = int(traj['n_frames'])
    dt_ms = int(traj['dt_ms'])
    phase = traj['phase']

    if len(phase) != n_frames:
        raise ValueError(f'phase 长度 {len(phase)} != n_frames {n_frames}')

    for ch in channels:
        if len(traj_channels[ch]) != n_frames:
            raise ValueError(f'通道 {ch} 长度 {len(traj_channels[ch])} != n_frames {n_frames}')

    return {
        'sample_id': traj['sample_id'],
        'emotion': traj['emotion'],
        'intensity': traj['intensity'],
        'dt_ms': dt_ms,
        'n_frames': n_frames,
        'phase': np.asarray(phase, dtype=np.float32),
        'matrix': np.stack(
            [np.asarray(traj_channels[ch], dtype=np.float32) for ch in channels],
            axis=-1,
        ),
        'ornament_type': traj.get('aux_labels', {}).get('ornament_type', 'none'),
        'returns_to_neutral': bool(traj.get('aux_labels', {}).get('returns_to_neutral', True)),
        'source': traj.get('meta', {}).get('source', 'unknown'),
        'total_duration_ms': int(traj.get('meta', {}).get('total_duration_ms', 0)),
    }


def resample_sample_to_target_frames(sample, target_frames):
    if target_frames <= 1:
        raise ValueError('target_frames 必须大于 1')

    target_phase = np.linspace(0.0, 1.0, target_frames, dtype=np.float32)
    source_phase = sample['phase']
    source_matrix = sample['matrix']

    resampled_columns = []
    for col_idx in range(source_matrix.shape[1]):
        resampled_columns.append(
            np.interp(target_phase, source_phase, source_matrix[:, col_idx]).astype(np.float32)
        )

    resampled_matrix = np.stack(resampled_columns, axis=-1)
    normalized = dict(sample)
    normalized['phase'] = target_phase
    normalized['matrix'] = resampled_matrix
    normalized['n_frames'] = target_frames
    return normalized


def normalize_samples_to_target_frames(samples, target_frames):
    return [resample_sample_to_target_frames(sample, target_frames) for sample in samples]


def ensure_same_layout(samples, channels):
    if not samples:
        raise ValueError('没有样本')

    ref_dt = samples[0]['dt_ms']
    ref_frames = samples[0]['n_frames']
    ref_phase = samples[0]['phase']

    for sample in samples[1:]:
        if sample['dt_ms'] != ref_dt:
            raise ValueError(f"dt_ms 不一致: {sample['sample_id']}={sample['dt_ms']} vs ref={ref_dt}")
        if sample['n_frames'] != ref_frames:
            raise ValueError(f"n_frames 不一致: {sample['sample_id']}={sample['n_frames']} vs ref={ref_frames}")
        if not np.allclose(sample['phase'], ref_phase, atol=1e-6):
            raise ValueError(f"phase 不一致: {sample['sample_id']} 与参考样本不同，请先统一重采样")

    return ref_dt, ref_frames, ref_phase


def build_dataset(samples, channels):
    x_3d = np.stack([sample['matrix'] for sample in samples], axis=0).astype(np.float32)
    x_flat = x_3d.reshape(x_3d.shape[0], -1).astype(np.float32)

    return {
        'X_3d': x_3d,
        'X_flat': x_flat,
        'sample_ids': np.asarray([sample['sample_id'] for sample in samples], dtype=object),
        'emotions': np.asarray([sample['emotion'] for sample in samples], dtype=object),
        'intensities': np.asarray([sample['intensity'] for sample in samples], dtype=object),
        'ornament_types': np.asarray([sample['ornament_type'] for sample in samples], dtype=object),
        'returns_to_neutral': np.asarray([sample['returns_to_neutral'] for sample in samples], dtype=bool),
        'channels': np.asarray(channels, dtype=object),
        'phase': samples[0]['phase'].astype(np.float32),
        'dt_ms': np.asarray([samples[0]['dt_ms']], dtype=np.int32),
        'n_frames': np.asarray([samples[0]['n_frames']], dtype=np.int32),
    }


def save_npz(path: Path, dataset):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **dataset)


def group_by_intensity(samples):
    groups = {}
    for sample in samples:
        groups.setdefault(sample['intensity'], []).append(sample)
    return groups


def main():
    parser = argparse.ArgumentParser(description='把 .traj.json 批量整理成 ProMP 训练矩阵')
    parser.add_argument('input_dir', help='输入目录，例如 data/happy_promp/processed')
    parser.add_argument('--output-dir', default=None, help='输出目录，默认 <input_dir>/matrix_out')
    parser.add_argument(
        '--channels',
        nargs='+',
        default=DEFAULT_CHANNELS,
        help='要抽取的训练通道',
    )
    parser.add_argument(
        '--target-frames',
        type=int,
        default=None,
        help='将所有样本重采样到统一帧数后再组矩阵',
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else (input_dir / 'matrix_out')
    channels = args.channels
    target_frames = args.target_frames

    files = list_traj_files(input_dir)

    samples = []
    metadata_rows = []

    for file in files:
        traj = load_json(file)
        sample = validate_and_extract(traj, channels)
        samples.append(sample)
        metadata_rows.append({
            'sample_id': sample['sample_id'],
            'emotion': sample['emotion'],
            'intensity': sample['intensity'],
            'dt_ms': sample['dt_ms'],
            'n_frames': sample['n_frames'],
            'ornament_type': sample['ornament_type'],
            'returns_to_neutral': sample['returns_to_neutral'],
            'source': sample['source'],
            'total_duration_ms': sample['total_duration_ms'],
            'file_name': file.name,
        })

    if target_frames is not None:
        samples = normalize_samples_to_target_frames(samples, target_frames)

    ensure_same_layout(samples, channels)

    all_dataset = build_dataset(samples, channels)
    metadata_rows = [
        {
            **row,
            'n_frames': samples[idx]['n_frames'],
        }
        for idx, row in enumerate(metadata_rows)
    ]
    save_npz(output_dir / 'all_samples.npz', all_dataset)

    groups = group_by_intensity(samples)
    for intensity, group_samples in groups.items():
        ds = build_dataset(group_samples, channels)
        save_npz(output_dir / f'happy_{intensity}.npz', ds)

    save_metadata_csv(output_dir / 'metadata.csv', metadata_rows)

    print(f'[DONE] total_samples={len(samples)}')
    print(f'[DONE] channels={channels}')
    print(f'[DONE] output_dir={output_dir}')
    print('[DONE] saved: all_samples.npz, metadata.csv')
    for intensity, group_samples in groups.items():
        print(f'[DONE] saved: happy_{intensity}.npz ({len(group_samples)} samples)')


if __name__ == '__main__':
    main()
