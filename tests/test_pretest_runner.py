from pretest_runner import build_pretest_manifest, summarize_pretest_run


def test_build_pretest_manifest_repeats_each_condition_and_builds_stimulus_key():
    conditions = [
        {
            "block": "block2_dynamic_comparison",
            "emotion": "happy",
            "condition": "fixed",
            "config": {"demo_seconds": 5},
        },
        {
            "block": "block3_targeted_ablation",
            "pair": "sad_posture",
            "emotion": "sad",
            "condition": "posture_ablation",
            "config": {"demo_seconds": 6},
        },
    ]

    rows = build_pretest_manifest(conditions, repeats=3)

    assert len(rows) == 6
    assert rows == [
        {
            "stimulus_key": "block2_dynamic_comparison__happy__fixed",
            "block": "block2_dynamic_comparison",
            "emotion": "happy",
            "pair": None,
            "condition": "fixed",
            "trial_index": 1,
            "config": {"demo_seconds": 5},
        },
        {
            "stimulus_key": "block2_dynamic_comparison__happy__fixed",
            "block": "block2_dynamic_comparison",
            "emotion": "happy",
            "pair": None,
            "condition": "fixed",
            "trial_index": 2,
            "config": {"demo_seconds": 5},
        },
        {
            "stimulus_key": "block2_dynamic_comparison__happy__fixed",
            "block": "block2_dynamic_comparison",
            "emotion": "happy",
            "pair": None,
            "condition": "fixed",
            "trial_index": 3,
            "config": {"demo_seconds": 5},
        },
        {
            "stimulus_key": "block3_targeted_ablation__sad__sad_posture__posture_ablation",
            "block": "block3_targeted_ablation",
            "emotion": "sad",
            "pair": "sad_posture",
            "condition": "posture_ablation",
            "trial_index": 1,
            "config": {"demo_seconds": 6},
        },
        {
            "stimulus_key": "block3_targeted_ablation__sad__sad_posture__posture_ablation",
            "block": "block3_targeted_ablation",
            "emotion": "sad",
            "pair": "sad_posture",
            "condition": "posture_ablation",
            "trial_index": 2,
            "config": {"demo_seconds": 6},
        },
        {
            "stimulus_key": "block3_targeted_ablation__sad__sad_posture__posture_ablation",
            "block": "block3_targeted_ablation",
            "emotion": "sad",
            "pair": "sad_posture",
            "condition": "posture_ablation",
            "trial_index": 3,
            "config": {"demo_seconds": 6},
        },
    ]



def test_build_pretest_manifest_defaults_to_three_repeats_and_preserves_config_identity():
    config = {"demo_seconds": 4}
    conditions = [
        {
            "block": "block2_dynamic_comparison",
            "emotion": "fearful",
            "condition": "dynamic",
            "config": config,
        }
    ]

    rows = build_pretest_manifest(conditions)

    assert [row["trial_index"] for row in rows] == [1, 2, 3]
    assert all(row["config"] is config for row in rows)



def test_summarize_pretest_run_marks_stability_and_overall_pass_when_all_checks_hold():
    summary = summarize_pretest_run(
        stimulus_key="block2_dynamic_comparison__happy__fixed",
        repeated_runs=[True, True, True],
        cue_visible=True,
        safe_to_record=True,
    )

    assert summary == {
        "stimulus_key": "block2_dynamic_comparison__happy__fixed",
        "successful_runs": 3,
        "attempted_runs": 3,
        "stability_passed": True,
        "cue_visible": True,
        "safe_to_record": True,
        "passes_pretest": True,
    }



def test_summarize_pretest_run_fails_overall_if_any_run_or_gate_fails():
    summary = summarize_pretest_run(
        stimulus_key="block3_targeted_ablation__sad__sad_posture__posture_ablation",
        repeated_runs=[True, False, True],
        cue_visible=False,
        safe_to_record=True,
    )

    assert summary == {
        "stimulus_key": "block3_targeted_ablation__sad__sad_posture__posture_ablation",
        "successful_runs": 2,
        "attempted_runs": 3,
        "stability_passed": False,
        "cue_visible": False,
        "safe_to_record": True,
        "passes_pretest": False,
    }



def test_summarize_pretest_run_fails_when_no_repeated_runs_are_attempted():
    summary = summarize_pretest_run(
        stimulus_key="block2_dynamic_comparison__happy__fixed",
        repeated_runs=[],
        cue_visible=True,
        safe_to_record=True,
    )

    assert summary == {
        "stimulus_key": "block2_dynamic_comparison__happy__fixed",
        "successful_runs": 0,
        "attempted_runs": 0,
        "stability_passed": False,
        "cue_visible": True,
        "safe_to_record": True,
        "passes_pretest": False,
    }
