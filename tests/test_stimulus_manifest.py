from stimulus_manifest import build_stimulus_manifest


def test_build_stimulus_manifest_assigns_anonymized_ids_and_preserves_analysis_fields():
    approved_rows = [
        {
            "block": "block1_emotion_perception",
            "emotion": "happy",
            "condition": "full",
            "config": {"sequence": [1]},
        },
        {
            "block": "block2_dynamic_comparison",
            "emotion": "happy",
            "condition": "dynamic",
            "config": {"sequence": [2]},
        },
        {
            "block": "block3_targeted_ablation",
            "emotion": "sad",
            "pair": "sad_posture",
            "condition": "posture_ablation",
            "config": {"sequence": [3]},
        },
    ]

    manifest = build_stimulus_manifest(approved_rows)

    assert manifest == [
        {
            "stimulus_id": "S001",
            "video_file_name": "S001.mp4",
            "block": "block1_emotion_perception",
            "analysis_emotion": "happy",
            "analysis_condition": "full",
            "analysis_pair": None,
            "config": {"sequence": [1]},
        },
        {
            "stimulus_id": "S002",
            "video_file_name": "S002.mp4",
            "block": "block2_dynamic_comparison",
            "analysis_emotion": "happy",
            "analysis_condition": "dynamic",
            "analysis_pair": None,
            "config": {"sequence": [2]},
        },
        {
            "stimulus_id": "S003",
            "video_file_name": "S003.mp4",
            "block": "block3_targeted_ablation",
            "analysis_emotion": "sad",
            "analysis_condition": "posture_ablation",
            "analysis_pair": "sad_posture",
            "config": {"sequence": [3]},
        },
    ]



def test_build_stimulus_manifest_does_not_expose_emotion_labels_in_video_file_names():
    approved_rows = [
        {
            "block": "block2_dynamic_comparison",
            "emotion": "fearful",
            "condition": "dynamic",
            "config": {"type": "demo"},
        }
    ]

    manifest = build_stimulus_manifest(approved_rows)

    assert manifest[0]["video_file_name"] == "S001.mp4"
    assert "fearful" not in manifest[0]["video_file_name"]
    assert "dynamic" not in manifest[0]["video_file_name"]
