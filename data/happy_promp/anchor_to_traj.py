#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
from pathlib import Path


CHANNELS = [
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


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_anchor_timeline(anchor_data):
    anchors = anchor_data['anchors']
    if not anchors:
        raise ValueError('anchors 不能为空')

    anchor_times_ms = []
    current = 0
    for anchor in anchors:
        anchor_times_ms.append(current)
        duration = int(anchor['duration_ms'])
        if duration <= 0:
            raise ValueError(f'非法 duration_ms: {duration}')
        current += duration

    return anchors, anchor_times_ms, current


def linear_interp(x, xp, fp):
    if x <= xp[0]:
        return fp[0]
    if x >= xp[-1]:
        return fp[-1]

    for i in range(len(xp) - 1):
        x0, x1 = xp[i], xp[i + 1]
        if x0 <= x <= x1:
            y0, y1 = fp[i], fp[i + 1]
            if x1 == x0:
                return y0
            ratio = (x - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)

    return fp[-1]


def build_target_times(total_duration_ms, dt_ms):
    if dt_ms <= 0:
        raise ValueError('dt_ms 必须 > 0')

    n_frames = int(round(total_duration_ms / dt_ms)) + 1
    times = [i * dt_ms for i in range(n_frames)]
    if times[-1] != total_duration_ms:
        times[-1] = total_duration_ms
    return times


def anchors_to_channel_series(anchors, anchor_times_ms, total_duration_ms):
    xp = list(anchor_times_ms) + [total_duration_ms]
    channel_map = {}

    for ch in CHANNELS:
        values = [float(anchor[ch]) for anchor in anchors]
        values.append(float(anchors[-1][ch]))
        channel_map[ch] = {
            'xp': xp,
            'fp': values,
        }

    return channel_map


def resample_channels(channel_map, target_times_ms):
    result = {}
    for ch, series in channel_map.items():
        xp = series['xp']
        fp = series['fp']
        result[ch] = [round(linear_interp(t, xp, fp), 6) for t in target_times_ms]
    return result


def normalize_phase(target_times_ms, total_duration_ms):
    if total_duration_ms <= 0:
        return [0.0 for _ in target_times_ms]
    return [round(t / total_duration_ms, 6) for t in target_times_ms]


def convert_anchor_to_traj(anchor_data, dt_ms):
    anchors, anchor_times_ms, total_duration_ms = build_anchor_timeline(anchor_data)
    channel_map = anchors_to_channel_series(anchors, anchor_times_ms, total_duration_ms)
    target_times_ms = build_target_times(total_duration_ms, dt_ms)
    channels = resample_channels(channel_map, target_times_ms)
    phase = normalize_phase(target_times_ms, total_duration_ms)

    ornament_values = [
        anchor.get('ornament', 'none')
        for anchor in anchors
        if anchor.get('ornament', 'none') not in ('none', 'recover')
    ]
    ornament_type = ornament_values[0] if ornament_values else 'none'

    return {
        'sample_id': anchor_data['sample_id'],
        'emotion': anchor_data['emotion'],
        'intensity': anchor_data['intensity'],
        'dt_ms': dt_ms,
        'n_frames': len(target_times_ms),
        'phase': phase,
        'time_ms': target_times_ms,
        'channels': channels,
        'fixed_fields': anchor_data.get('fixed_fields', {}),
        'aux_labels': {
            'ornament_type': ornament_type,
            'returns_to_neutral': bool(anchor_data.get('returns_to_neutral', True)),
        },
        'meta': {
            'source': anchor_data.get('source', 'unknown'),
            'total_duration_ms': total_duration_ms,
            'anchor_count': len(anchors),
        },
    }


def default_output_path(input_path: Path, output_path):
    if output_path is not None:
        return output_path
    return input_path.with_suffix('').with_suffix('.traj.json')


def process_one_file(input_path: Path, output_path, dt_ms: int):
    anchor_data = load_json(input_path)
    traj_data = convert_anchor_to_traj(anchor_data, dt_ms)
    out_path = default_output_path(input_path, output_path)
    save_json(out_path, traj_data)
    return out_path, traj_data['n_frames']


def process_directory(input_dir: Path, output_dir: Path, dt_ms: int):
    files = sorted(input_dir.glob('*.anchor.json'))
    if not files:
        raise FileNotFoundError(f'目录下没有找到 *.anchor.json: {input_dir}')

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for file in files:
        anchor_data = load_json(file)
        traj_data = convert_anchor_to_traj(anchor_data, dt_ms)
        out_path = output_dir / file.name.replace('.anchor.json', '.traj.json')
        save_json(out_path, traj_data)
        results.append((file, out_path, traj_data['n_frames']))

    return results


def main():
    parser = argparse.ArgumentParser(description='从 .anchor.json 自动插值生成 .traj.json')
    parser.add_argument('input', help='输入文件或目录')
    parser.add_argument('--output', default=None, help='输出文件或目录')
    parser.add_argument('--dt-ms', type=int, default=50, help='重采样步长（毫秒）')
    args = parser.parse_args()

    input_path = Path(args.input)
    output_arg = Path(args.output) if args.output else None

    if input_path.is_file():
        out_path, n_frames = process_one_file(input_path, output_arg, args.dt_ms)
        print(f'[OK] {input_path} -> {out_path} ({n_frames} frames)')
        return

    if input_path.is_dir():
        output_dir = output_arg or (input_path.parent / 'processed')
        results = process_directory(input_path, output_dir, args.dt_ms)
        for src, dst, n_frames in results:
            print(f'[OK] {src.name} -> {dst.name} ({n_frames} frames)')
        print(f'[DONE] total={len(results)} files, output_dir={output_dir}')
        return

    raise FileNotFoundError(f'输入不存在: {input_path}')


if __name__ == '__main__':
    main()
