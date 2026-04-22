# CyberDog2 Emotion Control Alignment Design

## Goal

Align the current CyberDog2 emotion-control project with `六情绪动作开发.pdf`, keeping the existing hand-authored parameter configuration plus LCM command pipeline, while fixing logic bugs in execution flow and making the project easier to modify safely.

## Scope

This work updates the current direct-control implementation only.

Included:
- Delete legacy residual files that are no longer part of the active architecture.
- Treat `六情绪动作开发.pdf` as the sole authority for emotion definitions and motion requirements.
- Extract executable requirements from the PDF and map them to the current code.
- Correct mismatches between the PDF and the implementation.
- Fix execution-flow bugs in the current motion sequencing logic.
- Add local tests that validate configuration correctness and motion sequencing behavior without requiring a robot.

Excluded:
- No PAD emotion generation architecture.
- No redesign of the LCM protocol layer.
- No refactor unrelated to PDF alignment, maintainability of the active path, or current execution correctness.
- No manual edits to generated LCM message classes.

## Maintainability Requirements

The active project path must remain easy to modify after this work.

That means:
- emotion behavior should be driven primarily by `config.py`, not by hard-coded emotion-name branches in entrypoints
- file responsibilities must stay clear and narrow enough that changing configuration does not require understanding unrelated LCM internals
- sequencing logic must be centralized in `motion_sequence.py` instead of duplicated across callers
- tests must protect the expected behavior so future parameter or flow changes can be made with confidence
- fixes should prefer small, explicit structures over introducing a second architecture or speculative abstraction

## Files In Scope

Delete:
- `scripts/demo_refined_v1.py`
- `scripts/demo_rule_v1.py`
- `scripts/auto_lcm_init.sh:Zone.Identifier`

Preserve and update as needed:
- `main.py`
- `demo.py`
- `emotion.py`
- `config.py`
- `motion_sequence.py`
- `robot_control.py`

Read-only protocol files:
- `robot_control_cmd_lcmt.py`
- `robot_control_response_lcmt.py`

New files allowed:
- Local tests for configuration and sequencing logic.
- Local helper code only if needed to extract or check PDF-derived requirements.

## Source of Truth Strategy

`六情绪动作开发.pdf` is the only authority for motion intent and required behavior.

The implementation process is:
1. Read the PDF and convert each emotion into an executable specification.
2. For each emotion, capture:
   - emotion name
   - single vs loop behavior
   - ordered motion steps
   - `mode`
   - `gait_id`
   - velocity, posture, height, position, and timing requirements when specified
   - required final stop motion when specified
3. Mark any PDF item as unspecified if the document does not define it clearly.
4. Compare the extracted specification against the codebase.
5. Change only the parts needed to make code behavior match the document.

## Architecture Boundaries

The current architecture remains in place, with responsibilities clarified:

- `config.py` stores emotion configurations and motion-step definitions.
- `emotion.py` defines the emotion set and emotion lookup surface.
- `motion_sequence.py` executes motion sequences according to configuration.
- `main.py` provides CLI execution behavior.
- `demo.py` provides demonstration flow across emotions.
- `robot_control.py` translates steps into LCM command publication and receives LCM responses.

Emotion semantics must live in configuration and sequencing layers, not be spread across ad hoc conditionals in entrypoint code.

This boundary is also the main maintainability rule:
- changing an emotion should usually mean editing `config.py`
- changing execution behavior should usually mean editing `motion_sequence.py`
- changing transport details should usually mean editing `robot_control.py`
- `main.py` and `demo.py` should stay thin orchestration layers

## Execution Model Corrections

The current code path has a structural risk: loop motions execute in a blocking path, while `main.py` and `demo.py` assume they can start a loop, wait, and later stop it externally.

The corrected model is:

### Single motions
- Execute synchronously.
- Run each step exactly once in order.
- Reset execution state on completion.

### Loop motions
- Execute asynchronously in a background worker thread.
- Allow callers to regain control immediately after start.
- Continue running until `stop()` is requested.
- When stopped, exit the loop cleanly.
- If the emotion defines a `stop_motion`, execute it exactly once during shutdown.
- Reset execution state after the worker exits.

### Stop semantics
`stop()` must become the single consistent stop entrypoint. It should:
- request stop
- wait for loop execution to exit when a loop worker exists
- execute configured stop motion when required by the emotion
- restore clean internal state

### Entrypoint behavior
`main.py` and `demo.py` must stop inferring behavior from hard-coded emotion-name lists. They should use configuration type and explicit rules derived from the PDF-aligned configuration.

## Validation Strategy

Validation happens in two stages.

### Stage 1: Local non-robot validation
Use local tests with a fake controller object that records `send_command()` calls.

This validates:
- single motions send the expected ordered steps
- loop motions repeat correctly
- `stop()` stops loops cleanly
- `stop_motion` is emitted when configured
- execution-state flags are correct before, during, and after runs

### Stage 2: Configuration consistency validation
Add tests that verify:
- the emotion set matches the authority document
- each emotion has a valid configuration shape
- each emotion is classified correctly as single or loop
- required fields exist for each step
- PDF-aligned expectations remain enforced over time

### Stage 3: Real robot validation
Real robot validation remains necessary for final confirmation of expressive behavior, but it is not required for initial logic verification.

Local completion means the sequencing logic and configuration structure are correct. Final emotional expressiveness still requires on-robot observation.

## Risk Management

Known risks addressed by this design:
- Legacy scripts may confuse the active architecture.
- Emotion definitions in code may diverge from the document.
- Loop motion control may not match caller expectations.
- Hard-coded entrypoint behavior may drift from configuration and document intent.

This design addresses them by removing dead artifacts, centralizing behavior in configuration plus sequencer logic, and testing sequencing without hardware.

## Success Criteria

The work is successful when:
- the active code path matches the PDF-defined emotion set and motion behavior
- loop motions can be started and stopped predictably
- single motions complete cleanly and reset state correctly
- `main.py` and `demo.py` no longer rely on ad hoc emotion-name branching for core behavior
- changing or adding an emotion mostly requires configuration updates rather than cross-file logic edits
- legacy generator-demo remnants are removed
- local tests cover the corrected behavior without requiring robot hardware

## Notes

This repository is not currently a git repository, so the design document cannot be committed in the normal workflow. The document should still be reviewed before implementation planning begins.
