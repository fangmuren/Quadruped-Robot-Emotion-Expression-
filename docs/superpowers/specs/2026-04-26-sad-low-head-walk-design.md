# Sad Low-Head Walk Design

## Goal

Adjust the `sad` emotion so it reads more clearly on the real robot:
- first lower the body
- then hold a visibly sad low-head pose in place
- then perform a short low-head slow walk
- then keep the existing sit-down ending

The change should improve the chance that the low-head posture remains visible during locomotion while keeping the current project structure intact.

## Scope

Included:
- Update only the `sad` sequence in `config_fixed.py`
- Preserve the current execution pipeline in `motion_sequence.py`, `main.py`, and `robot_control.py`
- Keep the existing sit-down ending for `sad`
- Favor a stable, moderate posture over an extreme pitch target

Excluded:
- No changes to other emotions
- No refactor of sequencing logic or transport logic
- No change to the `sad` high-level narrative order
- No attempt to guarantee a permanent seated end state after the sit action

## Root Cause Summary

The current `sad` sequence mixes pose control and locomotion:
- a pose-control step creates the visible head-down posture
- a later locomotion step starts slow walking

On the real robot, entering locomotion can hand posture control back to the locomotion stabilizer. That means the visible pose from the earlier pose-control step may not carry forward reliably into walking, even when the locomotion step also includes `rpy`.

This is why the current single long locomotion step can appear to return toward a neutral balanced posture.

## Design Choice

Use the existing sequence shape, keep the stationary low-head pose clearly negative, then restore a locomotion-friendly body height and enter a single short locomotion step with a confirmed positive walking pitch.

This preserves the emotional beat the user wants:
1. lower height
2. hold a sad pose in place
3. restore height for locomotion and walk a short distance while still reading as sad
4. sit down

## Alternatives Considered

### Option 1: Tune the current single locomotion step
Chosen after robot verification. Smallest diff, preserves the existing sequence shape, and the confirmed positive walking pitch reads more clearly on the robot than keeping a negative pitch through locomotion.

### Option 2: Split the walk into multiple short locomotion steps
Still viable as a fallback if future robot runs show the walking posture recenters too aggressively, but no longer the preferred design.

### Option 3: Remove the stationary pose step and do everything through locomotion
Avoids a pose-to-walk handoff, but loses the important emotional beat where the robot first pauses in a sad head-down pose.

## Recommended Implementation

Modify only the `sad.sequence` block in `config_fixed.py`.

Keep these existing steps:
- recovery stand
- lower body height with `mode=21, gait_id=5`
- stationary low-head pose with `mode=21, gait_id=0`
- final sit action with `mode=62, gait_id=3`

Preserve the current single locomotion step, but keep the inserted body-height reset immediately before it.

### Step behavior

#### Stationary pose step
Keep a clearly visible low-head pause before walking starts. This is the main emotional setup beat and should remain more pronounced than the walk itself.

#### Height-reset step
Restore the body to a locomotion-friendly height before entering slow walk so the gait controller starts from a more stable posture.

#### Locomotion step
The locomotion command should:
- keep the same slow backward walking intent
- use the restored locomotion body height rather than the lower stationary pose height
- include the confirmed positive pitch target in `rpy[1]`
- remain short enough that the sad pose still reads before the sit action

### Parameter direction

Use moderate values rather than aggressive ones:
- keep backward velocity slightly slower than the original baseline
- use a negative pitch only for the stationary pose step
- use a moderate positive pitch during locomotion because that is the robot-verified sad walking posture
- keep durations long enough to read, but avoid adding extra locomotion segments unless future robot tuning requires them

## File Impact

Modify:
- `config_fixed.py`

No changes planned for:
- `config.py`
- `emotion.py`
- `motion_sequence.py`
- `main.py`
- `robot_control.py`

## Verification

Real-robot verification should focus on observable behavior rather than transport changes.

Minimum checks:
1. The robot lowers and holds a sad head-down pose before moving.
2. During the short walk, the head-down posture remains visibly present instead of snapping quickly back to neutral.
3. The walk remains short and controlled.
4. The final sit action still triggers.

Non-goals for this change:
- guaranteeing that the robot stays seated forever after the sit primitive
- redesigning how sit completion is handled

## Success Criteria

This design succeeds if:
- `sad` still follows the same high-level story
- the low-head posture is more visible during the walking portion than it is now
- the change is limited to `config_fixed.py`
- no other emotion behavior is affected
