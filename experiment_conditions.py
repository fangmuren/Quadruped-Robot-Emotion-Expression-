from copy import deepcopy

from emotion import get_emotion_config


def _get_config(emotion, rho, lambda_weight):
    return deepcopy(get_emotion_config(emotion, rho=rho, lambda_weight=lambda_weight))


def _build_posture_ablation(emotion, rho, lambda_weight):
    config = _get_config(emotion, rho, lambda_weight)
    for step in config.get("sequence", []):
        if "body_height" in step:
            step["body_height"] = 0.22
        if "rpy" in step and len(step["rpy"]) >= 2:
            step["rpy"][1] = 0.0
    return config


def _build_rhythm_ablation(emotion, rho, lambda_weight):
    config = _get_config(emotion, rho, lambda_weight)
    for step in config.get("sequence", []):
        if step.get("duration", 0) >= 1000:
            step["duration"] = 400
    return config


_CONDITION_BUILDERS = {
    "fixed": lambda emotion, rho, lambda_weight: deepcopy(get_emotion_config(emotion)),
    "dynamic": _get_config,
    "posture_ablation": _build_posture_ablation,
    "rhythm_ablation": _build_rhythm_ablation,
    "lambda_zero": lambda emotion, rho, lambda_weight: deepcopy(
        get_emotion_config(emotion, rho=rho, lambda_weight=0.0)
    ),
    "full": _get_config,
}


def build_condition_config(emotion, condition, rho, lambda_weight):
    if condition not in _CONDITION_BUILDERS:
        raise ValueError(f"Unknown condition: {condition}")
    return _CONDITION_BUILDERS[condition](emotion, rho, lambda_weight)


def build_block2_conditions(rho, lambda_weight):
    rows = []
    for emotion in ("happy", "sad", "fearful", "angry"):
        for condition in ("fixed", "dynamic"):
            rows.append(
                {
                    "block": "block2_dynamic_comparison",
                    "emotion": emotion,
                    "condition": condition,
                    "config": build_condition_config(emotion, condition, rho, lambda_weight),
                }
            )
    return rows


def build_block3_conditions(rho, lambda_weight):
    rows = []
    block3_specs = [
        ("sad_posture", "sad", ("full", "posture_ablation")),
        ("fear_rhythm", "fearful", ("full", "rhythm_ablation")),
        ("happy_surprise", "happy", ("full", "lambda_zero")),
        ("anger_surprise", "angry", ("full", "lambda_zero")),
    ]

    for pair, emotion, conditions in block3_specs:
        for condition in conditions:
            rows.append(
                {
                    "block": "block3_targeted_ablation",
                    "pair": pair,
                    "emotion": emotion,
                    "condition": condition,
                    "config": build_condition_config(emotion, condition, rho, lambda_weight),
                }
            )
    return rows
