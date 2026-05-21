def _build_stimulus_key(block, emotion, condition, pair=None):
    parts = [block, emotion]
    if pair is not None:
        parts.append(pair)
    parts.append(condition)
    return "__".join(parts)



def build_pretest_manifest(conditions, repeats=3):
    rows = []
    for condition_row in conditions:
        block = condition_row["block"]
        emotion = condition_row["emotion"]
        pair = condition_row.get("pair")
        condition = condition_row["condition"]
        config = condition_row["config"]
        stimulus_key = _build_stimulus_key(block, emotion, condition, pair=pair)

        for trial_index in range(1, repeats + 1):
            rows.append(
                {
                    "stimulus_key": stimulus_key,
                    "block": block,
                    "emotion": emotion,
                    "pair": pair,
                    "condition": condition,
                    "trial_index": trial_index,
                    "config": config,
                }
            )
    return rows



def summarize_pretest_run(stimulus_key, repeated_runs, cue_visible, safe_to_record):
    successful_runs = sum(1 for run in repeated_runs if run)
    attempted_runs = len(repeated_runs)
    stability_passed = attempted_runs > 0 and successful_runs == attempted_runs
    passes_pretest = stability_passed and cue_visible and safe_to_record

    return {
        "stimulus_key": stimulus_key,
        "successful_runs": successful_runs,
        "attempted_runs": attempted_runs,
        "stability_passed": stability_passed,
        "cue_visible": cue_visible,
        "safe_to_record": safe_to_record,
        "passes_pretest": passes_pretest,
    }
