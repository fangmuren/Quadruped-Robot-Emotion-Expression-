import json
from pathlib import Path

from data.happy_promp.sample_happy_promp import load_model, reconstruct_trajectory


DEFAULT_SAMPLE_ID = 'happy_promp_runtime'
DEFAULT_EMOTION = 'happy'
DEFAULT_INTENSITY = 'mid'
DEFAULT_MODE = 11
DEFAULT_GAIT_ID = 27
DEFAULT_VELOCITY_Y = 0.0
DEFAULT_RPY_ROLL = 0.0
DEFAULT_RPY_YAW = 0.0
DEFAULT_PREPARATION_STEPS = [
    {'mode': 12, 'gait_id': 0, 'duration': 6000},
    {'mode': 21, 'gait_id': 5, 'body_height': 0.24, 'duration': 400},
]
DEFAULT_FINISH_STEP = {'mode': 3, 'gait_id': 0, 'body_height': 0.23, 'duration': 600}
REQUIRED_CHANNELS = [
    'velocity_x',
    'yaw_rate',
    'step_height_left',
    'step_height_right',
    'body_height',
    'pitch',
]


def build_deterministic_traj(model_path, sample_id=DEFAULT_SAMPLE_ID, emotion=DEFAULT_EMOTION, intensity=DEFAULT_INTENSITY):
    model = load_model(Path(model_path))
    channel_map = reconstruct_trajectory(model, model['mu_w'])
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


def summarize_traj(traj):
    channels = traj['channels']
    total_duration_ms = traj['dt_ms'] * max(traj['n_frames'] - 1, 0)
    return {
        'n_frames': traj['n_frames'],
        'dt_ms': traj['dt_ms'],
        'total_duration_ms': total_duration_ms,
        'channel_ranges': {
            name: {
                'min': min(values),
                'max': max(values),
            }
            for name, values in channels.items()
        },
    }


def write_traj(path, traj):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as handle:
        json.dump(traj, handle, ensure_ascii=False, indent=2)


def _validate_traj(traj):
    for key in ('dt_ms', 'n_frames', 'phase', 'time_ms', 'channels'):
        if key not in traj:
            raise ValueError(f'missing traj field: {key}')

    channels = traj['channels']
    for channel in REQUIRED_CHANNELS:
        if channel not in channels:
            raise ValueError(f'missing channel: {channel}')
        if len(channels[channel]) != traj['n_frames']:
            raise ValueError(f'channel length mismatch for {channel}')


def traj_to_steps(traj):
    _validate_traj(traj)
    steps = []
    channels = traj['channels']
    for index in range(traj['n_frames']):
        steps.append({
            'mode': DEFAULT_MODE,
            'gait_id': DEFAULT_GAIT_ID,
            'velocity': [
                channels['velocity_x'][index],
                DEFAULT_VELOCITY_Y,
                channels['yaw_rate'][index],
            ],
            'step_height': [
                channels['step_height_left'][index],
                channels['step_height_right'][index],
            ],
            'body_height': channels['body_height'][index],
            'rpy': [
                DEFAULT_RPY_ROLL,
                channels['pitch'][index],
                DEFAULT_RPY_YAW,
            ],
            'duration': traj['dt_ms'],
        })
    return steps


class ModelTrajectoryRunner:
    def __init__(self, controller_factory=None):
        self.controller_factory = controller_factory

    def _create_controller(self):
        if self.controller_factory is not None:
            return self.controller_factory()
        from robot_control import CyberDogController
        return CyberDogController()

    def run_model(self, model_path, dry_run=False, save_traj_path=None):
        traj = build_deterministic_traj(model_path)
        if save_traj_path is not None:
            write_traj(save_traj_path, traj)
        return self.run_traj(traj, dry_run=dry_run)

    def run_traj(self, traj, dry_run=False):
        steps = traj_to_steps(traj)
        summary = summarize_traj(traj)
        if dry_run:
            return {
                'status': 'dry_run',
                'traj': traj,
                'steps': steps,
                'summary': summary,
            }

        controller = self._create_controller()
        try:
            for step in DEFAULT_PREPARATION_STEPS:
                controller.send_command(**step)
            for step in steps:
                controller.send_command(**step)
            controller.send_command(**DEFAULT_FINISH_STEP)
            return {
                'status': 'completed',
                'traj': traj,
                'steps': steps,
                'summary': summary,
            }
        except KeyboardInterrupt:
            try:
                controller.send_command(**DEFAULT_FINISH_STEP)
            except Exception:
                pass
            raise
        except Exception:
            try:
                controller.send_command(**DEFAULT_FINISH_STEP)
            except Exception:
                pass
            raise
        finally:
            controller.close()


def run_model(model_path, dry_run=False, save_traj_path=None):
    return ModelTrajectoryRunner().run_model(
        model_path,
        dry_run=dry_run,
        save_traj_path=save_traj_path,
    )


def run_traj(traj, dry_run=False):
    return ModelTrajectoryRunner().run_traj(traj, dry_run=dry_run)
