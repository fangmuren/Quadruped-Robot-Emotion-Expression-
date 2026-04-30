# Sad Locomotion Pitch Tuning Design

## Goal

Tune the `sad` emotion so the robot keeps a more visible head-down feeling after locomotion takes over.

The immediate problem is not that the stationary low-head pose is missing. The problem is that once `mode=11, gait_id=27` begins, the robot quickly lifts back toward its locomotion balance posture and the backward walk no longer reads as sad.

## Scope

Included:
- Adjust only the three segmented locomotion steps in the `sad` sequence in `config_fixed.py`
- Preserve the current high-level emotional flow:
  - lower body
  - hold a low-head pose
  - short backward walk
  - sit down
- Favor a balanced result: keep the backward walk and improve the low-head trend without pushing either to an extreme

Excluded:
- No changes to other emotions
- No changes to sequencing logic or transport logic
- No redesign of the `sad` pose-control step before locomotion
- No attempt to solve this by adding new execution code outside configuration

## Root Cause Summary

The current real-robot observation is:
- the head-down pose is visible before walking
- as soon as the first locomotion segment starts, the head lifts quickly
- during backward motion it is difficult to perceive a continuing low-head trend

This suggests the locomotion controller is quickly reasserting its own balance solution after takeover. In that situation, simply increasing pitch is not necessarily the best first adjustment. A more effective first move is to reduce locomotion aggressiveness so the controller has less reason to recenter posture.

## Design Choice

Use a minimal tuning pass that keeps the three-step segmented locomotion structure, but makes those segments gentler.

The tuning priority is:
1. reduce backward speed slightly
2. keep a moderate negative pitch target rather than an extreme one
3. reduce step height slightly only if needed after the first pass

This aims to preserve both parts of the user's desired feel:
- still visibly walking backward
- still visibly sad during locomotion

## Alternatives Considered

### Option 1: Increase negative pitch only
Smallest single-parameter change, but likely too weak against fast locomotion recentering. It may exaggerate the transition moment without improving the sustained sad trend.

### Option 2: Reduce speed and step aggressiveness while keeping moderate negative pitch
Recommended. This reduces locomotion load on the balance controller and gives the commanded low-head posture a better chance to remain visible.

### Option 3: Split the walk into even more segments
Could reassert the posture target more often, but adds configuration complexity before testing the simpler explanation that the current walk is just too dynamically aggressive.

## Recommended Tuning Pass

Modify only the three `mode=11, gait_id=27` sad locomotion steps in `config_fixed.py`.

### First tuning pass
- Lower `velocity[0]` slightly from the current values
- Keep `rpy[1]` in a moderate negative range rather than driving it much more negative
- Leave the segment count at three
- Keep the pre-walk low-head pose and final sit action unchanged

### Second tuning pass, only if the first still recenters too quickly
- Lower `step_height` slightly on the same three locomotion steps
- Keep all other emotions and all non-locomotion sad steps unchanged

## Parameter Direction

For the next experiment, tune in this order:

1. `velocity[0]`
   - decrease first
   - goal: reduce the controller's need to recenter under motion load

2. `rpy[1]`
   - keep clearly negative but avoid treating pitch magnitude as the primary lever
   - goal: retain a sad trend without forcing an unstable pose target

3. `step_height`
   - use as the third lever if speed reduction alone is not enough
   - goal: make the gait less dynamically demanding

## File Impact

Modify:
- `config_fixed.py`

No changes planned for:
- `motion_sequence.py`
- `robot_control.py`
- `main.py`
- `demo.py`
- current tests, unless a later implementation chooses to lock the new tuned values explicitly

## Verification

Real-robot verification should answer these questions:
1. Does the head still lift immediately on the first locomotion segment?
2. Is the backward walk still clearly present?
3. Is there now a visible low-head trend during the walk rather than only before it?
4. Does the final sit action still look correct?

The first tuning pass succeeds if the robot still walks backward and the sad low-head feeling remains visible for more of the locomotion portion than before.

## Success Criteria

This tuning design succeeds if:
- the robot no longer appears to snap upright immediately at locomotion takeover
- backward movement remains visible
- changes stay limited to the three sad locomotion steps
- no unrelated emotion behavior changes are introduced
