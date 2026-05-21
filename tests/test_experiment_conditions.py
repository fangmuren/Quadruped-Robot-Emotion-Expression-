from unittest.mock import patch

from experiment_conditions import (
    build_block2_conditions,
    build_block3_conditions,
    build_condition_config,
)
from emotion import get_emotion_config


def test_build_condition_config_returns_config_object_not_wrapper_row():
    rho = 0.35
    lambda_weight = 1.2

    full = build_condition_config("sad", "full", rho, lambda_weight)
    fixed = build_condition_config("sad", "fixed", rho, lambda_weight)
    dynamic = build_condition_config("sad", "dynamic", rho, lambda_weight)
    lambda_zero = build_condition_config("sad", "lambda_zero", rho, lambda_weight)

    assert full == get_emotion_config("sad", rho=rho, lambda_weight=lambda_weight)
    assert fixed == get_emotion_config("sad")
    assert dynamic == get_emotion_config("sad", rho=rho, lambda_weight=lambda_weight)
    assert lambda_zero == get_emotion_config("sad", rho=rho, lambda_weight=0.0)
    assert "emotion" not in full
    assert "condition" not in full
    assert "config" not in full


def test_all_condition_builders_return_independent_config_objects():
    rho = 0.35
    lambda_weight = 1.2
    conditions = (
        "fixed",
        "dynamic",
        "full",
        "lambda_zero",
        "posture_ablation",
        "rhythm_ablation",
    )

    for condition in conditions:
        first = build_condition_config("sad", condition, rho, lambda_weight)
        second = build_condition_config("sad", condition, rho, lambda_weight)

        assert first == second
        assert first is not second
        if "sequence" in first and first["sequence"]:
            assert first["sequence"] is not second["sequence"]
            assert first["sequence"][0] is not second["sequence"][0]


def test_posture_ablation_neutralizes_body_height_and_zeroes_pitch_only():
    rho = 0.35
    lambda_weight = 1.2

    full = build_condition_config("sad", "full", rho, lambda_weight)
    ablated = build_condition_config("sad", "posture_ablation", rho, lambda_weight)

    assert ablated["type"] == full["type"]
    assert ablated["demo_seconds"] == full["demo_seconds"]
    assert len(ablated["sequence"]) == len(full["sequence"])

    body_height_checked = False
    pitch_checked = False
    for full_step, ablated_step in zip(full["sequence"], ablated["sequence"]):
        if "body_height" in full_step:
            body_height_checked = True
            assert ablated_step["body_height"] == 0.22
        if "rpy" in full_step:
            pitch_checked = True
            assert ablated_step["rpy"][0] == full_step["rpy"][0]
            assert ablated_step["rpy"][1] == 0.0
            assert ablated_step["rpy"][2] == full_step["rpy"][2]

    assert body_height_checked
    assert pitch_checked


def test_rhythm_ablation_flattens_only_long_durations_to_400ms():
    rho = 0.35
    lambda_weight = 1.2
    mocked_config = {
        "type": "mocked",
        "demo_seconds": 1,
        "sequence": [
            {"duration": 200},
            {"duration": 1000},
            {"duration": 1500, "body_height": 0.18},
            {"duration": 999, "rpy": [0.1, 0.2, 0.3]},
            {"body_height": 0.22},
        ],
    }

    with patch("experiment_conditions.get_emotion_config", return_value=mocked_config):
        ablated = build_condition_config("sad", "rhythm_ablation", rho, lambda_weight)

    assert len(ablated["sequence"]) == len(mocked_config["sequence"])
    assert [step.get("duration") for step in ablated["sequence"]] == [200, 400, 400, 999, None]
    assert ablated["sequence"][2]["body_height"] == 0.18
    assert ablated["sequence"][3]["rpy"] == [0.1, 0.2, 0.3]
    assert mocked_config["sequence"][1]["duration"] == 1000
    assert mocked_config["sequence"][2]["duration"] == 1500
    assert mocked_config["sequence"][3]["duration"] == 999


def test_build_block2_conditions_covers_four_emotions_by_two_conditions():
    rows = build_block2_conditions(rho=0.4, lambda_weight=0.8)

    assert len(rows) == 8
    assert all(row["block"] == "block2_dynamic_comparison" for row in rows)
    assert [(row["emotion"], row["condition"]) for row in rows] == [
        ("happy", "fixed"),
        ("happy", "dynamic"),
        ("sad", "fixed"),
        ("sad", "dynamic"),
        ("fearful", "fixed"),
        ("fearful", "dynamic"),
        ("angry", "fixed"),
        ("angry", "dynamic"),
    ]
    assert all(set(row) == {"block", "emotion", "condition", "config"} for row in rows)


def test_build_block3_conditions_covers_named_condition_pairs():
    rows = build_block3_conditions(rho=0.25, lambda_weight=1.5)

    assert all(row["block"] == "block3_targeted_ablation" for row in rows)
    assert [(row["pair"], row["condition"]) for row in rows] == [
        ("sad_posture", "full"),
        ("sad_posture", "posture_ablation"),
        ("fear_rhythm", "full"),
        ("fear_rhythm", "rhythm_ablation"),
        ("happy_surprise", "full"),
        ("happy_surprise", "lambda_zero"),
        ("anger_surprise", "full"),
        ("anger_surprise", "lambda_zero"),
    ]

    assert rows[0]["emotion"] == "sad"
    assert rows[2]["emotion"] == "fearful"
    assert rows[4]["emotion"] == "happy"
    assert rows[6]["emotion"] == "angry"
    assert all(set(row) == {"block", "pair", "emotion", "condition", "config"} for row in rows)
