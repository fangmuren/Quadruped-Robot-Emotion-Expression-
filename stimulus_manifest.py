def build_stimulus_manifest(approved_rows):
    manifest = []

    for index, approved_row in enumerate(approved_rows, start=1):
        stimulus_id = f"S{index:03d}"
        manifest.append(
            {
                "stimulus_id": stimulus_id,
                "video_file_name": f"{stimulus_id}.mp4",
                "block": approved_row["block"],
                "analysis_emotion": approved_row["emotion"],
                "analysis_condition": approved_row["condition"],
                "analysis_pair": approved_row.get("pair"),
                "config": approved_row["config"],
            }
        )

    return manifest
