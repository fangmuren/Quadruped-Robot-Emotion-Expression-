# Traj-to-Robot Executor Design

Date: 2026-05-11

## Goal

Add a minimal viable execution path that accepts a `data/happy_promp/models/*.npz` ProMP model and plays it on the robot without requiring the user to manually generate an intermediate `traj.json`.

The first version is intentionally narrow:

- Input is `model.npz`
- Playback is deterministic
- Runtime parameters use fixed happy defaults
- The executor runs through a standalone CLI entrypoint
- The executor performs automatic preparation and automatic safe finish

## Non-goals

This version does not attempt to:

- support stochastic sampling during execution
- merge into the existing `main.py` emotion entrypoint
- support arbitrary per-run mode or gait overrides
- perform closed-loop correction from robot feedback
- retry failed frame sends
- support non-happy models or non-locomotion control modes

## Existing Context

The current runtime already has a stable command path:

- `main.py` starts the controller and sequence runner
- `motion_sequence.py` sends step dictionaries into the controller
- `robot_control.py` converts step fields into LCM messages
- `robot_control_cmd_lcmt.py` defines the wire format

The ProMP pipeline already supports:

- loading `model.npz`
- reconstructing a deterministic trajectory from `mu_w`
- generating a `traj`-shaped in-memory structure matching the sampled happy data format

What does not exist yet is the adapter layer between a reconstructed `traj` and the robot runtime step format.

## Recommended Architecture

Keep the existing runtime flow unchanged and add a new standalone execution path.

### 1. ModelLoader / TrajBuilder

Responsibility:

- load `model.npz`
- reconstruct a deterministic trajectory using `mu_w`
- produce an in-memory `traj` structure

Inputs:

- path to `model.npz`

Outputs:

- in-memory object with:
  - `dt_ms`
  - `n_frames`
  - `phase`
  - `time_ms`
  - `channels`

Notes:

- reuse the logic pattern from `data/happy_promp/sample_happy_promp.py`
- do not require saving a `traj.json` file before execution
- deterministic playback means no random sampling and no runtime seed handling in v1

### 2. TrajStepAdapter

Responsibility:

- convert each trajectory frame into the existing step dictionary shape already understood by `motion_sequence.py` and `robot_control.py`

Inputs:

- in-memory `traj`

Outputs:

- iterable or list of step dictionaries

Fixed runtime defaults for v1:

- `mode = 11`
- `gait_id = 27`
- `velocity_y = 0.0`
- `rpy_roll = 0.0`
- `rpy_yaw = 0.0`

Per-frame mapping:

- `channels.velocity_x[i] -> velocity[0]`
- `0.0 -> velocity[1]`
- `channels.yaw_rate[i] -> velocity[2]`
- `channels.step_height_left[i] -> step_height[0]`
- `channels.step_height_right[i] -> step_height[1]`
- `channels.body_height[i] -> body_height`
- `0.0 -> rpy[0]`
- `channels.pitch[i] -> rpy[1]`
- `0.0 -> rpy[2]`
- `dt_ms -> duration`
- constant `11 -> mode`
- constant `27 -> gait_id`

Example output frame:

```python
{
    "mode": 11,
    "gait_id": 27,
    "velocity": [0.062, 0.0, 0.12],
    "step_height": [0.025, 0.025],
    "body_height": 0.245,
    "rpy": [0.0, 0.08, 0.0],
    "duration": 50,
}
```

Constraint note:

- the dataset uses `step_height_left/right` naming while the runtime consumes a 2-element `step_height` vector
- for this first version, map them positionally as `[left, right]`
- because the current happy samples are symmetric, this keeps behavior stable enough for the first real-robot path
- if future trajectories use asymmetric leg semantics, the adapter contract must be revisited explicitly

### 3. ModelTrajectoryRunner

Responsibility:

- own controller lifecycle for the standalone path
- execute fixed preparation motions
- stream trajectory-derived steps to the robot
- execute fixed finish motions
- handle interruption and best-effort safe shutdown

Inputs:

- model path
- step sequence from `TrajStepAdapter`

Outputs:

- process exit status and console logs

## Execution Flow

The standalone executor should follow this exact sequence:

1. initialize `CyberDogController`
2. load and reconstruct deterministic trajectory from `model.npz`
3. adapt trajectory frames into runtime steps
4. send preparation motions
5. play all trajectory steps in order
6. send finish motion
7. close controller

### Preparation motions

Before sending the model-derived locomotion frames, always send:

1. recovery stand
   - `mode = 12`
   - `gait_id = 0`
   - `duration = 6000ms`
2. happy standing height
   - `mode = 21`
   - `gait_id = 5`
   - `body_height = 0.24`
   - `duration = 400ms`

These values match the existing happy runtime pattern and reduce the risk of hard switching directly into locomotion.

### Finish motion

After all frames have been sent, always send a short finish motion:

- `mode = 3`
- `gait_id = 0`
- `body_height = 0.23` to `0.24`
- `duration = 600ms`

For the first implementation, pick a single explicit value rather than a range. The design recommendation is `0.23` for a slightly safer settle.

## CLI Shape

Expose a standalone script entrypoint, for example:

```bash
python3 run_promp_model.py data/happy_promp/models/happy_mid_promp.npz
```

Minimal CLI arguments for v1:

- positional `model_npz`
- `--dry-run`
- `--print-summary`
- `--save-traj <path>`

### CLI semantics

Default behavior:

- reconstruct from `mu_w`
- do not sample randomly
- use fixed happy runtime defaults
- automatically run preparation and finish motions

Option behavior:

- `--dry-run`: build trajectory and step sequence without connecting to the robot
- `--print-summary`: print model path, frame count, `dt_ms`, total duration, and per-channel min/max ranges
- `--save-traj <path>`: write the deterministic in-memory trajectory to disk for inspection

## Error Handling and Safety

This version keeps failure behavior intentionally simple.

### Failures before execution

If model loading or deterministic reconstruction fails:

- print the error
- do not start playback
- if the controller was already created, close it
- return a non-zero exit code

### Failures during playback

If a frame send raises an exception:

- stop sending future frames immediately
- attempt the finish motion once
- close the controller
- return a non-zero exit code

### User interruption

If the user presses `Ctrl+C` during preparation, playback, or finish:

- stop scheduling future frames
- attempt the finish motion once
- close the controller
- exit cleanly with an interrupted status

### Out-of-scope for v1

The executor will not yet:

- inspect `order_process_bar` before advancing frames
- wait for per-frame motion completion feedback
- retry failed sends
- fuse model playback with neutral background behavior

## Logging

Use simple stdout logging only.

At minimum print:

- controller startup
- model path loaded
- frame count, `dt_ms`, total duration
- preparation motion start
- playback start
- per-frame progress at a coarse cadence, not every frame if that becomes noisy
- finish motion start
- completion, interruption, or failure reason
- controller shutdown

## Testing Strategy

### 1. Model reconstruction tests

Given an existing `model.npz` fixture:

- reconstruct deterministic trajectory successfully
- assert required top-level fields exist
- assert `n_frames`, `dt_ms`, and each required channel are populated

### 2. Traj-to-step adapter tests

Given a small synthetic `traj`:

- assert `mode == 11`
- assert `gait_id == 27`
- assert `pitch -> rpy[1]`
- assert `yaw_rate -> velocity[2]`
- assert `body_height -> body_height`
- assert `dt_ms -> duration`
- assert step ordering matches frame ordering

### 3. Runner orchestration tests

Using a fake controller:

- assert commands are sent in this order:
  1. preparation motion 1
  2. preparation motion 2
  3. trajectory frames
  4. finish motion
- assert `Ctrl+C` or injected exceptions stop future frame scheduling
- assert the finish motion is attempted once on interruption or send failure

### 4. Dry-run tests

- assert `--dry-run` does not instantiate or use the real controller
- assert optional `--save-traj` produces a file containing deterministic trajectory data

## Acceptance Criteria

The minimal viable executor is complete when all of the following are true:

1. a user can execute `model.npz` directly through a standalone CLI
2. playback is deterministic and does not vary across runs
3. preparation motions always run before model-derived locomotion frames
4. each model frame is converted into the existing controller step format and sent in order
5. finish motion always runs after normal completion
6. `Ctrl+C` stops future frame playback and attempts the finish motion
7. dry-run mode allows inspection of the generated trajectory and step path without robot access

## Recommended File Placement

Suggested additions:

- `run_promp_model.py` — CLI entrypoint
- `promp_runtime.py` — model loader, adapter, and runner helpers
- new tests alongside the existing happy ProMP pipeline tests

The key design rule is to keep model execution isolated from the current emotion configuration path so the new feature can be validated on the real robot without destabilizing the existing `main.py` workflow.
