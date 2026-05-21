"""Public emotion accessors.

The stable public baseline comes from ``EMOTION_CONFIGS``. Callers that pass
optional tuning parameters opt into generated facade-backed configs instead.
"""

from config_fixed import (
    DEFAULT_LAMBDA_WEIGHT,
    DEFAULT_RHO,
    EMOTION_CONFIGS,
    generate_behavior_plan,
    generate_emotion_configs,
)


def _resolve_configs(rho, lambda_weight):
    if rho is None and lambda_weight == DEFAULT_LAMBDA_WEIGHT:
        return EMOTION_CONFIGS
    resolved_rho = DEFAULT_RHO if rho is None else rho
    return generate_emotion_configs(rho=resolved_rho, lambda_weight=lambda_weight)


def _resolve_behavior_plan(emotion, rho, lambda_weight):
    resolved_rho = DEFAULT_RHO if rho is None else rho
    return generate_behavior_plan(emotion, rho=resolved_rho, lambda_weight=lambda_weight)


def _validate_vector(name: str, value, expected_length: int):
    if len(value) != expected_length:
        raise ValueError(f"{name} must have length {expected_length}")


def validate_emotion_config(emotion: str, config: dict):
    if config['type'] not in {'single', 'loop'}:
        raise ValueError(f"{emotion}.type must be 'single' or 'loop'")
    if 'demo_seconds' not in config:
        raise ValueError(f"{emotion}.demo_seconds is required")
    if 'sequence' not in config or not isinstance(config['sequence'], list) or not config['sequence']:
        raise ValueError(f"{emotion}.sequence must be a non-empty list")

    for index, step in enumerate(config['sequence']):
        step_name = f"{emotion}.sequence[{index}]"
        if 'mode' not in step:
            raise ValueError(f"{step_name}.mode is required")
        if 'gait_id' not in step:
            raise ValueError(f"{step_name}.gait_id is required")
        duration = step.get('duration', 0)
        if duration < 0:
            raise ValueError(f"{step_name}.duration must be >= 0")
        if 'velocity' in step:
            _validate_vector(f"{step_name}.velocity", step['velocity'], 3)
        if 'position' in step:
            _validate_vector(f"{step_name}.position", step['position'], 3)
        if 'rpy' in step:
            _validate_vector(f"{step_name}.rpy", step['rpy'], 3)
        if 'step_height' in step:
            _validate_vector(f"{step_name}.step_height", step['step_height'], 2)


class SixEmotions:
    HAPPY = 'happy'
    SAD = 'sad'
    FEARFUL = 'fearful'
    ANGRY = 'angry'
    DISGUSTED = 'disgusted'
    SURPRISED = 'surprised'

    ALL = [HAPPY, SAD, FEARFUL, ANGRY, DISGUSTED, SURPRISED]


def get_behavior_plan(emotion: str, rho: float = DEFAULT_RHO, lambda_weight: float = DEFAULT_LAMBDA_WEIGHT) -> dict:
    if emotion not in SixEmotions.ALL:
        raise ValueError(f"Unknown emotion: {emotion}. Must be one of {SixEmotions.ALL}")
    plan = _resolve_behavior_plan(emotion, rho, lambda_weight)
    validate_emotion_config(emotion, plan['compiled_config'])
    return plan


def get_emotion_config(emotion: str, rho: float = None, lambda_weight: float = DEFAULT_LAMBDA_WEIGHT) -> dict:
    """Return the public baseline config by default, or a tuned generated config.

    The no-tuning path preserves the stable public contract backed by
    ``EMOTION_CONFIGS``. Supplying ``rho`` and/or ``lambda_weight`` switches to
    generated facade-backed configs for optional tuning workflows.
    """
    configs = _resolve_configs(rho, lambda_weight)
    if emotion not in configs:
        raise ValueError(f"Unknown emotion: {emotion}. Must be one of {SixEmotions.ALL}")
    config = configs[emotion]
    validate_emotion_config(emotion, config)
    return config


def get_all_emotions() -> list:
    return SixEmotions.ALL


def get_runtime_policy(emotion: str):
    config = get_emotion_config(emotion)
    return config['type'], config['demo_seconds']


def get_sequence_duration_seconds(emotion: str) -> float:
    config = get_emotion_config(emotion)
    return sum(step.get('duration', 0) for step in config['sequence']) / 1000.0


def get_post_execute_wait_seconds(emotion: str) -> float:
    config = get_emotion_config(emotion)
    if config['type'] == 'single':
        return 0.0
    return max(config['demo_seconds'], get_sequence_duration_seconds(emotion))
