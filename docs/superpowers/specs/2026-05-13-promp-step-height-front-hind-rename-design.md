# ProMP Step Height Front/Hind Rename Design

Date: 2026-05-13

## Goal

Rename all ProMP-local legacy step-height channel names inside the `traj-to-robot-executor` worktree to `step_height_front` / `step_height_hind` so the trajectory channel naming matches front-leg vs hind-leg semantics.

## Scope

This change applies only to the worktree at `traj-to-robot-executor`.

Included:

- runtime code
- data preprocessing scripts
- raw anchor data
- processed trajectory JSON
- tests
- worktree-local specs and plans

Excluded:

- the main workspace outside this worktree
- the robot controller interface
- the top-level `step_height` 2-element command field used when sending commands to the robot

## Non-goals

This change does not:

- introduce a compatibility layer for old names
- change robot command wire format
- change the meaning or ordering of the runtime `step_height` vector
- refactor unrelated ProMP or controller code

## Existing Context

The worktree currently uses legacy step-height names in three places:

1. ProMP data and preprocessing channel names
2. runtime validation and per-frame mapping in `promp_runtime.py`
3. tests and worktree-local design docs

The runtime already converts trajectory channels into the controller-facing command shape:

- trajectory channels are named fields inside `traj['channels']`
- robot playback still expects `step_height: [front, hind]`

That controller-facing `step_height` vector stays unchanged in this design.

## Recommended Approach

Apply a full in-worktree rename with no compatibility aliasing.

### Why this approach

- keeps the whole ProMP worktree internally consistent
- avoids carrying two naming schemes forward
- keeps the rename isolated from the main workspace and robot interface
- makes any missed references fail fast in tests because runtime channel validation is strict

## Detailed Design

### 1. Data and preprocessing

Rename the raw anchor-data step-height channel keys from the legacy left/right names to:

- `step_height_front`
- `step_height_hind`

Apply the same rename in processed trajectory JSON channel maps.

Update preprocessing scripts so their ordered channel lists and required field expectations use the new names:

- `data/happy_promp/anchor_to_traj.py`
- `data/happy_promp/traj_to_matrix.py`

The positional meaning remains:

- `front` = first step-height channel
- `hind` = second step-height channel

### 2. Runtime mapping

Update `promp_runtime.py` so all internal channel references use `step_height_front/hind`:

- clamp range lookup keys
- required channel names
- per-frame channel extraction
- any validation error messages derived from required channels

The runtime output sent to the controller remains:

```python
'step_height': [front, hind]
```

Conceptually the mapping becomes:

- `channels.step_height_front[i] -> step_height[0]`
- `channels.step_height_hind[i] -> step_height[1]`

No robot-side API change is required.

### 3. Tests and docs

Update all ProMP worktree tests so fixtures, expected channel names, and assertions use `front/hind`:

- `tests/test_promp_runtime.py`
- `tests/test_happy_promp_data_pipeline.py`

Update worktree-local specs and plans so examples and prose no longer reference `left/right` names.

## Error Handling and Compatibility

No backward-compatibility path will be added.

If any legacy step-height names remain in data or tests, the runtime or tests should fail immediately rather than silently accepting mixed naming.

This is intentional because the rename is scoped to a single isolated worktree.

## Risks

The main risk is partial renaming, especially in:

- raw anchor JSON
- processed trajectory JSON
- expected ordered channel lists
- test fixtures
- spec or plan snippets that are later copied back into code

This risk is controlled by treating the rename as an all-or-nothing worktree-wide update and then verifying there are no remaining legacy step-height references.

## Verification

Verification must include:

1. global search inside the `traj-to-robot-executor` worktree confirms no remaining legacy step-height names
2. ProMP runtime tests pass
3. ProMP data pipeline tests pass
4. runtime still produces controller commands with `step_height: [front, hind]`

## Acceptance Criteria

The work is complete when all of the following are true:

1. no legacy left/right step-height references remain anywhere in the `traj-to-robot-executor` worktree
2. raw data, processed data, scripts, tests, and worktree-local docs all use `step_height_front/hind`
3. `promp_runtime.py` requires and consumes `step_height_front/hind`
4. controller-facing runtime commands still use `step_height: [front, hind]`
5. ProMP-related tests pass without adding compatibility fallbacks
