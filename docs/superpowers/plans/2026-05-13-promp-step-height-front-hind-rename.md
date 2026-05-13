# ProMP Step Height Front/Hind Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename every ProMP-local malformed step-height reference inside the `traj-to-robot-executor` worktree to clear front/hind wording while preserving controller-facing `step_height: [front, hind]` playback commands.

**Architecture:** Treat this as a worktree-wide data-contract rename. First update the runtime and pipeline unit tests to describe the new contract, then update the runtime and preprocessing code, then rewrite the checked-in JSON and regenerated `.npz` artifacts so `build_deterministic_traj()` reconstructs front/hind channels from the stored models, and finally clean the local docs plus run a no-leftovers verification pass.

**Tech Stack:** Python 3, stdlib `json`/`pathlib`/`argparse`, NumPy `.npz` artifacts, existing ProMP scripts under `data/happy_promp/`, stdlib `unittest`, `pytest`, ripgrep

---

### File Structure

- `promp_runtime.py` — runtime-required channel names, clamping, and mapping from ProMP channels into controller-facing `step_height: [front, hind]`.
- `tests/test_promp_runtime.py` — runtime adapter, runner, and deterministic model reconstruction tests.
- `data/happy_promp/anchor_to_traj.py` — raw anchor JSON to processed trajectory JSON conversion; owns anchor channel ordering.
- `data/happy_promp/traj_to_matrix.py` — processed trajectory JSON to training matrix export; owns dataset channel ordering.
- `tests/test_happy_promp_data_pipeline.py` — pipeline unit tests for anchor conversion, matrix export, and on-disk artifact naming.
- `data/happy_promp/raw/happy_{low,mid,high}_001.anchor.json` — checked-in raw anchor samples that must use `step_height_front/hind`.
- `data/happy_promp/processed/happy_{low,mid,high}_001.traj.json` — checked-in processed trajectories that must expose `channels.step_height_front/hind`.
- `data/happy_promp/matrix/{all_samples,happy_low,happy_mid,happy_high}.npz` and `data/happy_promp/matrix/metadata.csv` — regenerated training datasets; `.npz` files must store the new channel names.
- `data/happy_promp/models/happy_{low,mid,high}_promp.npz` — regenerated ProMP models; `channels` arrays must use `step_height_front/hind` so runtime reconstruction matches the new contract.
- `docs/superpowers/specs/2026-05-11-traj-to-robot-executor-design.md` — historical design doc that still references left/right channel names.
- `docs/superpowers/specs/2026-05-13-promp-step-height-front-hind-rename-design.md` — current spec that must be reworded so no malformed mixed-axis step-height strings remain after the rename.
- `docs/superpowers/plans/2026-05-11-traj-to-robot-executor.md` and `docs/superpowers/plans/2026-05-12-promp-remediation-phase1.md` — historical plans with examples and code blocks that must be updated to the new names.

### Task 1: Rename the runtime channel contract in tests and implementation

**Files:**
- Modify: `tests/test_promp_runtime.py`
- Modify: `promp_runtime.py`
- Test: `tests/test_promp_runtime.py`

- [ ] **Step 1: Change the runtime fixture and adapter tests to front/hind**

Edit `tests/test_promp_runtime.py` so the runtime fixture and adapter test expect `step_height_front/hind` as input channels while still asserting `step_height` is emitted as a two-element controller command:

```python
def make_two_frame_runner_traj():
    return {
        'dt_ms': 50,
        'n_frames': 2,
        'phase': [0.0, 1.0],
        'time_ms': [0, 50],
        'channels': {
            'velocity_x': [0.05, 0.06],
            'yaw_rate': [0.0, 0.1],
            'step_height_front': [0.02, 0.03],
            'step_height_hind': [0.02, 0.03],
            'body_height': [0.24, 0.25],
            'pitch': [0.02, 0.08],
        },
    }


def test_traj_to_steps_maps_velocity_x_and_clamps_runtime_channels(self):
    traj = {
        'dt_ms': 50,
        'n_frames': 2,
        'phase': [0.0, 1.0],
        'time_ms': [0, 50],
        'channels': {
            'velocity_x': [0.03, 0.088889],
            'yaw_rate': [-0.3, 0.3],
            'step_height_front': [-0.01, 0.06],
            'step_height_hind': [0.07, -0.02],
            'body_height': [0.2, 0.3],
            'pitch': [-0.1, 0.3],
        },
    }

    steps = traj_to_steps(traj)

    self.assertEqual(steps, [
        {
            'mode': 11,
            'gait_id': 27,
            'velocity': [0.2, 0.0, -0.25],
            'step_height': [0.0, 0.05],
            'body_height': 0.22,
            'rpy': [0.0, -0.05, 0.0],
            'duration': 50,
        },
        {
            'mode': 11,
            'gait_id': 27,
            'velocity': [0.4, 0.0, 0.25],
            'step_height': [0.05, 0.0],
            'body_height': 0.27,
            'rpy': [0.0, 0.2, 0.0],
            'duration': 50,
        },
    ])
```

- [ ] **Step 2: Run the targeted runtime tests and confirm they fail**

Run:

```bash
python3 -m pytest tests/test_promp_runtime.py -k "traj_to_steps_maps_velocity_x_and_clamps_runtime_channels or runner_sends_preparation_then_frames_then_finish or runner_paces_frames_and_emits_coarse_logs" -v
```

Expected: FAIL with a missing `step_height_front` / `step_height_hind` channel error from `traj_to_steps()` because `promp_runtime.py` still requires the old names.

- [ ] **Step 3: Update `promp_runtime.py` to require and consume front/hind channels**

Change the runtime channel constants and per-frame mapping in `promp_runtime.py` to this shape:

```python
CHANNEL_CLAMP_RANGES = {
    'yaw_rate': YAW_RATE_CLAMP_RANGE,
    'step_height_front': STEP_HEIGHT_CLAMP_RANGE,
    'step_height_hind': STEP_HEIGHT_CLAMP_RANGE,
    'body_height': BODY_HEIGHT_CLAMP_RANGE,
    'pitch': PITCH_CLAMP_RANGE,
}

REQUIRED_CHANNELS = [
    'velocity_x',
    'yaw_rate',
    'step_height_front',
    'step_height_hind',
    'body_height',
    'pitch',
]


def traj_to_steps(traj):
    _validate_traj(traj)
    steps = []
    channels = traj['channels']
    for index in range(traj['n_frames']):
        steps.append({
            'mode': DEFAULT_MODE,
            'gait_id': DEFAULT_GAIT_ID,
            'velocity': [
                map_velocity_x(channels['velocity_x'][index]),
                DEFAULT_VELOCITY_Y,
                clamp_channel_value('yaw_rate', channels['yaw_rate'][index]),
            ],
            'step_height': [
                clamp_channel_value('step_height_front', channels['step_height_front'][index]),
                clamp_channel_value('step_height_hind', channels['step_height_hind'][index]),
            ],
            'body_height': clamp_channel_value('body_height', channels['body_height'][index]),
            'rpy': [
                DEFAULT_RPY_ROLL,
                clamp_channel_value('pitch', channels['pitch'][index]),
                DEFAULT_RPY_YAW,
            ],
            'duration': traj['dt_ms'],
        })
    return steps
```

- [ ] **Step 4: Re-run the targeted runtime tests and confirm they pass**

Run:

```bash
python3 -m pytest tests/test_promp_runtime.py -k "traj_to_steps_maps_velocity_x_and_clamps_runtime_channels or runner_sends_preparation_then_frames_then_finish or runner_paces_frames_and_emits_coarse_logs" -v
```

Expected: PASS. The runtime should now accept front/hind input channels while still emitting controller commands that look like `step_height: [front, hind]`.

### Task 2: Rename the pipeline channel lists and unit-test fixtures

**Files:**
- Modify: `tests/test_happy_promp_data_pipeline.py`
- Modify: `data/happy_promp/anchor_to_traj.py`
- Modify: `data/happy_promp/traj_to_matrix.py`
- Test: `tests/test_happy_promp_data_pipeline.py`

- [ ] **Step 1: Update pipeline test fixtures and channel lists to front/hind**

Edit `tests/test_happy_promp_data_pipeline.py` so the inline anchor data, processed traj fixtures, and channel order assertions all use front/hind names:

```python
anchor = {
    'sample_id': 'happy_low_001',
    'emotion': 'happy',
    'intensity': 'low',
    'source': 'manual_seed',
    'fixed_fields': {
        'mode': 11,
        'gait_id': 27,
        'velocity_y': 0.0,
        'rpy_roll': 0.0,
        'rpy_yaw': 0.0,
        'position': [0.0, 0.0, 0.0],
    },
    'anchors': [
        {
            'phase': 'enter',
            'duration_ms': 100,
            'velocity_x': 0.03,
            'yaw_rate': 0.00,
            'step_height_front': 0.020,
            'step_height_hind': 0.020,
            'body_height': 0.236,
            'pitch': 0.00,
            'ornament': 'none',
        },
        {
            'phase': 'build',
            'duration_ms': 100,
            'velocity_x': 0.05,
            'yaw_rate': 0.10,
            'step_height_front': 0.024,
            'step_height_hind': 0.024,
            'body_height': 0.242,
            'pitch': 0.08,
            'ornament': 'nod_small',
        },
    ],
    'returns_to_neutral': True,
}

channels = [
    'velocity_x',
    'yaw_rate',
    'step_height_front',
    'step_height_hind',
    'body_height',
    'pitch',
]

self.assertEqual(traj['channels']['step_height_front'], [0.02, 0.022, 0.024, 0.024, 0.024])
```

Apply the same field rename to every inline `traj_low`, `traj_mid`, and `traj_high` fixture in that file.

- [ ] **Step 2: Run the targeted pipeline tests and confirm they fail**

Run:

```bash
python3 -m pytest tests/test_happy_promp_data_pipeline.py -k "anchor_to_traj_converts_anchor_segments_into_resampled_channels or traj_to_matrix_groups_samples_and_exports_expected_shapes or traj_to_matrix_normalizes_mixed_frame_counts_to_target_frames" -v
```

Expected: FAIL because `anchor_to_traj.py` and `traj_to_matrix.py` still declare malformed mixed-axis step-height wording in their ordered channel lists.

- [ ] **Step 3: Update the preprocessing scripts to use front/hind channel lists**

Change the ordered channel constants in both scripts to:

```python
CHANNELS = [
    'velocity_x',
    'yaw_rate',
    'step_height_front',
    'step_height_hind',
    'body_height',
    'pitch',
]
```

and:

```python
DEFAULT_CHANNELS = [
    'velocity_x',
    'yaw_rate',
    'step_height_front',
    'step_height_hind',
    'body_height',
    'pitch',
]
```

No other logic changes are needed in these two files; the rename is purely a checked-key and ordering update.

- [ ] **Step 4: Re-run the targeted pipeline tests and confirm they pass**

Run:

```bash
python3 -m pytest tests/test_happy_promp_data_pipeline.py -k "anchor_to_traj_converts_anchor_segments_into_resampled_channels or traj_to_matrix_groups_samples_and_exports_expected_shapes or traj_to_matrix_normalizes_mixed_frame_counts_to_target_frames" -v
```

Expected: PASS. The pipeline unit tests should now use the same front/hind channel names as the updated scripts.

### Task 3: Rewrite the checked-in raw and processed JSON fixtures

**Files:**
- Modify: `tests/test_happy_promp_data_pipeline.py`
- Modify: `data/happy_promp/raw/happy_low_001.anchor.json`
- Modify: `data/happy_promp/raw/happy_mid_001.anchor.json`
- Modify: `data/happy_promp/raw/happy_high_001.anchor.json`
- Modify: `data/happy_promp/processed/happy_low_001.traj.json`
- Modify: `data/happy_promp/processed/happy_mid_001.traj.json`
- Modify: `data/happy_promp/processed/happy_high_001.traj.json`
- Test: `tests/test_happy_promp_data_pipeline.py`

- [ ] **Step 1: Add a file-backed regression test for the checked-in JSON names**

Add this test method to `HappyPrompDataPipelineTest` in `tests/test_happy_promp_data_pipeline.py`:

```python
def test_repo_anchor_and_processed_files_use_front_hind_names(self):
    raw = json.loads((DATA_DIR / 'raw' / 'happy_low_001.anchor.json').read_text(encoding='utf-8'))
    first_anchor = raw['anchors'][0]
    self.assertIn('step_height_front', first_anchor)
    self.assertIn('step_height_hind', first_anchor)
    self.assertNotIn('step_height_front', first_anchor)
    self.assertNotIn('step_height_hind', first_anchor)

    traj = json.loads((DATA_DIR / 'processed' / 'happy_low_001.traj.json').read_text(encoding='utf-8'))
    self.assertIn('step_height_front', traj['channels'])
    self.assertIn('step_height_hind', traj['channels'])
    self.assertNotIn('step_height_front', traj['channels'])
    self.assertNotIn('step_height_hind', traj['channels'])
```

- [ ] **Step 2: Run the new file-backed test and confirm it fails**

Run:

```bash
python3 -m pytest tests/test_happy_promp_data_pipeline.py -k "repo_anchor_and_processed_files_use_front_hind_names" -v
```

Expected: FAIL because the checked-in JSON files still store the old keys.

- [ ] **Step 3: Rewrite the six checked-in JSON fixtures with a one-off script**

From the worktree root, run this exact script:

```bash
python3 - <<'PY'
from pathlib import Path
import json

paths = [
    Path('data/happy_promp/raw/happy_low_001.anchor.json'),
    Path('data/happy_promp/raw/happy_mid_001.anchor.json'),
    Path('data/happy_promp/raw/happy_high_001.anchor.json'),
    Path('data/happy_promp/processed/happy_low_001.traj.json'),
    Path('data/happy_promp/processed/happy_mid_001.traj.json'),
    Path('data/happy_promp/processed/happy_high_001.traj.json'),
]

for path in paths:
    data = json.loads(path.read_text(encoding='utf-8'))
    if path.name.endswith('.anchor.json'):
        for anchor in data['anchors']:
            anchor['step_height_front'] = anchor.pop('step_height_front')
            anchor['step_height_hind'] = anchor.pop('step_height_hind')
    else:
        channels = data['channels']
        channels['step_height_front'] = channels.pop('step_height_front')
        channels['step_height_hind'] = channels.pop('step_height_hind')
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'[DONE] {path}')
PY
```

- [ ] **Step 4: Re-run the file-backed JSON test and confirm it passes**

Run:

```bash
python3 -m pytest tests/test_happy_promp_data_pipeline.py -k "repo_anchor_and_processed_files_use_front_hind_names" -v
```

Expected: PASS. The repository fixtures should now contain only front/hind names.

### Task 4: Regenerate matrix datasets and ProMP models, then lock the deterministic model contract

**Files:**
- Modify: `tests/test_promp_runtime.py`
- Modify: `data/happy_promp/matrix/all_samples.npz`
- Modify: `data/happy_promp/matrix/happy_low.npz`
- Modify: `data/happy_promp/matrix/happy_mid.npz`
- Modify: `data/happy_promp/matrix/happy_high.npz`
- Modify: `data/happy_promp/matrix/metadata.csv`
- Modify: `data/happy_promp/models/happy_low_promp.npz`
- Modify: `data/happy_promp/models/happy_mid_promp.npz`
- Modify: `data/happy_promp/models/happy_high_promp.npz`
- Test: `tests/test_promp_runtime.py`

- [ ] **Step 1: Update the deterministic model reconstruction test to expect front/hind channels**

Edit the `test_build_deterministic_traj_reconstructs_expected_shape` assertion in `tests/test_promp_runtime.py` to:

```python
self.assertEqual(sorted(traj['channels'].keys()), [
    'body_height',
    'pitch',
    'step_height_front',
    'step_height_hind',
    'velocity_x',
    'yaw_rate',
])
self.assertNotIn('step_height_front', traj['channels'])
self.assertNotIn('step_height_hind', traj['channels'])
```

- [ ] **Step 2: Run the deterministic reconstruction tests and confirm they fail**

Run:

```bash
python3 -m pytest tests/test_promp_runtime.py -k "build_deterministic_traj_reconstructs_expected_shape or build_deterministic_traj_infers_low_and_high_intensity_from_model_filename" -v
```

Expected: FAIL because the checked-in `.npz` model files still store malformed mixed-axis step-height channel names in their `channels` arrays.

- [ ] **Step 3: Regenerate the matrix artifacts and the three checked-in ProMP models**

From the worktree root, run these commands in order:

```bash
python3 data/happy_promp/traj_to_matrix.py data/happy_promp/processed --output-dir data/happy_promp/matrix
python3 data/happy_promp/fit_happy_promp.py data/happy_promp/matrix/happy_low.npz --output data/happy_promp/models/happy_low_promp.npz --n-basis 8
python3 data/happy_promp/fit_happy_promp.py data/happy_promp/matrix/happy_mid.npz --output data/happy_promp/models/happy_mid_promp.npz --n-basis 8
python3 data/happy_promp/fit_happy_promp.py data/happy_promp/matrix/happy_high.npz --output data/happy_promp/models/happy_high_promp.npz --n-basis 8
```

Expected: the matrix script prints `[DONE] channels=['velocity_x', 'yaw_rate', 'step_height_front', 'step_height_hind', 'body_height', 'pitch']`, and each fit command rewrites its target model file.

- [ ] **Step 4: Inspect the regenerated dataset and model channel arrays**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import numpy as np

expected = ['velocity_x', 'yaw_rate', 'step_height_front', 'step_height_hind', 'body_height', 'pitch']
paths = [
    Path('data/happy_promp/matrix/all_samples.npz'),
    Path('data/happy_promp/matrix/happy_low.npz'),
    Path('data/happy_promp/matrix/happy_mid.npz'),
    Path('data/happy_promp/matrix/happy_high.npz'),
    Path('data/happy_promp/models/happy_low_promp.npz'),
    Path('data/happy_promp/models/happy_mid_promp.npz'),
    Path('data/happy_promp/models/happy_high_promp.npz'),
]
for path in paths:
    channels = np.load(path, allow_pickle=True)['channels'].tolist()
    assert channels == expected, (path.name, channels)
    print(f'[OK] {path.name}: {channels}')
PY
```

Expected: seven `[OK]` lines, all with the same front/hind channel order.

- [ ] **Step 5: Re-run the deterministic runtime tests and confirm they pass**

Run:

```bash
python3 -m pytest tests/test_promp_runtime.py -k "build_deterministic_traj_reconstructs_expected_shape or build_deterministic_traj_infers_low_and_high_intensity_from_model_filename" -v
```

Expected: PASS. `build_deterministic_traj()` should now reconstruct front/hind channel names directly from the checked-in models.

### Task 5: Update the worktree-local docs so no exact legacy names remain

**Files:**
- Modify: `docs/superpowers/specs/2026-05-11-traj-to-robot-executor-design.md`
- Modify: `docs/superpowers/specs/2026-05-13-promp-step-height-front-hind-rename-design.md`
- Modify: `docs/superpowers/plans/2026-05-11-traj-to-robot-executor.md`
- Modify: `docs/superpowers/plans/2026-05-12-promp-remediation-phase1.md`

- [ ] **Step 1: List the exact worktree-local docs that still contain the legacy field names**

Run:

```bash
rg -l -uu "step_height_(left|right)" docs/superpowers | sort
```

Expected: these four files only:

```text
docs/superpowers/plans/2026-05-11-traj-to-robot-executor.md
docs/superpowers/plans/2026-05-12-promp-remediation-phase1.md
docs/superpowers/specs/2026-05-11-traj-to-robot-executor-design.md
docs/superpowers/specs/2026-05-13-promp-step-height-front-hind-rename-design.md
```

- [ ] **Step 2: Apply token replacements to the three historical docs**

Run this exact script to update the two historical plans and the 2026-05-11 design doc:

```bash
python3 - <<'PY'
from pathlib import Path

targets = [
    Path('docs/superpowers/specs/2026-05-11-traj-to-robot-executor-design.md'),
    Path('docs/superpowers/plans/2026-05-11-traj-to-robot-executor.md'),
    Path('docs/superpowers/plans/2026-05-12-promp-remediation-phase1.md'),
]

for path in targets:
    text = path.read_text(encoding='utf-8')
    text = text.replace('step_height_front', 'step_height_front')
    text = text.replace('step_height_hind', 'step_height_hind')
    text = text.replace('[front, hind]', '[front, hind]')
    path.write_text(text, encoding='utf-8')
    print(f'[DONE] {path}')
PY
```

- [ ] **Step 3: Reword the current 2026-05-13 spec so it no longer contains the exact old names**

In `docs/superpowers/specs/2026-05-13-promp-step-height-front-hind-rename-design.md`, make these three exact replacements:

```text
Replace:
Rename all ProMP-local `step_height_front` / `step_height_hind` fields inside the `traj-to-robot-executor` worktree to `step_height_front` / `step_height_hind` so the trajectory channel naming matches front-leg vs hind-leg semantics.

With:
Rename all ProMP-local legacy step-height channel names inside the `traj-to-robot-executor` worktree to `step_height_front` / `step_height_hind` so the trajectory channel naming matches front-leg vs hind-leg semantics.
```

```text
Replace:
If any malformed mixed-axis step-height wording remains in data or tests, the runtime or tests should fail immediately rather than silently accepting mixed naming.

With:
If any legacy step-height names remain in data or tests, the runtime or tests should fail immediately rather than silently accepting mixed naming.
```

```text
Replace:
1. no malformed mixed-axis step-height references remain anywhere in the `traj-to-robot-executor` worktree

With:
1. no legacy left/right step-height references remain anywhere in the `traj-to-robot-executor` worktree
```

- [ ] **Step 4: Verify the docs are clean**

Run:

```bash
if rg -n -uu "step_height_(left|right)" docs/superpowers; then
  exit 1
else
  echo "[OK] docs cleaned"
fi
```

Expected: `[OK] docs cleaned`

### Task 6: Run the full verification pass for the worktree-wide rename

**Files:**
- Test: `tests/test_promp_runtime.py`
- Test: `tests/test_happy_promp_data_pipeline.py`

- [ ] **Step 1: Run the two ProMP test modules together**

Run:

```bash
python3 -m pytest tests/test_promp_runtime.py tests/test_happy_promp_data_pipeline.py -v
```

Expected: PASS for every test in both files.

- [ ] **Step 2: Verify there are no exact malformed mixed-axis step-height references left anywhere in the worktree**

Run:

```bash
if rg -n -uu "step_height_(left|right)" .; then
  exit 1
else
  echo "[OK] no legacy step-height field names remain in the worktree"
fi
```

Expected: `[OK] no legacy step-height field names remain in the worktree`

- [ ] **Step 3: Spot-check one runtime dry run to confirm controller-facing command shape is unchanged**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
from promp_runtime import build_deterministic_traj, traj_to_steps

model_path = Path('data/happy_promp/models/happy_mid_promp.npz')
traj = build_deterministic_traj(model_path)
first_step = traj_to_steps(traj)[0]
assert 'step_height' in first_step, first_step
assert len(first_step['step_height']) == 2, first_step
assert 'step_height_front' not in first_step, first_step
assert 'step_height_hind' not in first_step, first_step
print('[OK]', first_step['step_height'])
PY
```

Expected: `[OK] [...]` with a two-element list, proving the rename stayed inside the ProMP channel layer and did not leak into the controller API.
