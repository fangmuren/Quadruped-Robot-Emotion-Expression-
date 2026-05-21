"""Compatibility façade for chapter 3 behavior selection and compilation.

This module intentionally keeps the public Task 4 API stable while delegating
canonical affective rollout, PAD→BCP mapping, and primitive planning to the
accepted methodology modules:
- affective_state.py
- bcp_mapping.py
- behavior_planner.py
"""

from affective_state import (
    NEUTRAL_PAD,
    PAD_ANCHORS,
    compute_target_state,
    rollout_affective_episode,
    update_affective_state,
)
from bcp_mapping import state_to_bcp, trajectory_to_bcp_envelopes
from behavior_planner import (
    compile_behavior_plan_to_sequence as _compile_behavior_plan_to_sequence,
    select_behavior_plan,
)

SUPPORTED_EMOTIONS = tuple(PAD_ANCHORS)

_COMPAT_PHASE_NAME_MAP = (
    ('neutral_initialization', ('neutral_hold',)),
    ('posture_shaping', ('ramp_up',)),
    ('expressive_movement', ('expressive_peak', 'decay')),
    ('reinforcing_or_ending', ('return_to_neutral',)),
)


def _merge_compatibility_phases(canonical_phases):
    phases_by_name = {phase['name']: phase for phase in canonical_phases}
    compatibility_phases = []
    for compatibility_name, canonical_names in _COMPAT_PHASE_NAME_MAP:
        merged_states = []
        merged_targets = []
        merged_kappas = []
        for canonical_name in canonical_names:
            phase = phases_by_name.get(canonical_name)
            if not phase:
                continue
            merged_states.extend(phase.get('states', []))
            merged_targets.append(list(phase['target']))
            merged_kappas.append(phase['kappa'])
        compatibility_phases.append(
            {
                'name': compatibility_name,
                'canonical_phases': list(canonical_names),
                'target': merged_targets[-1] if merged_targets else list(NEUTRAL_PAD),
                'kappa': max(merged_kappas) if merged_kappas else 0.0,
                'states': merged_states,
            }
        )
    return compatibility_phases


def compile_behavior_plan_to_sequence(
    emotion: str,
    primitive_plan: dict,
):
    """Delegate runtime compilation to the planner-layer helper."""
    return _compile_behavior_plan_to_sequence(emotion, primitive_plan)


def build_behavior_plan(emotion: str, rho: float = 0.5, lambda_weight: float = 1.0):
    episode = rollout_affective_episode(emotion, rho=rho)
    envelopes = trajectory_to_bcp_envelopes(emotion, episode)
    primitive_plan = select_behavior_plan(emotion, envelopes, lambda_weight=lambda_weight)
    compiled_config = compile_behavior_plan_to_sequence(emotion, primitive_plan)
    return {
        'emotion': emotion,
        'rho': rho,
        'target_state': episode['target_state'],
        'trajectory': episode['trajectory'],
        'phases': episode['phases'],
        'bcp_envelopes': envelopes,
        'selected_primitives': primitive_plan['selected_primitives'],
        'confusion_margins': primitive_plan['confusion_margins'],
        'rejected_candidates': primitive_plan['rejected_candidates'],
        'compiled_config': compiled_config,
    }



def build_behavior_unit(emotion: str, rho: float = 0.5, lambda_weight: float = 1.0):
    """Build the legacy behavior-unit view from canonical planner outputs."""
    plan = build_behavior_plan(emotion, rho=rho, lambda_weight=lambda_weight)
    return {
        'emotion': plan['emotion'],
        'rho': plan['rho'],
        'target_state': plan['target_state'],
        'trajectory': plan['trajectory'],
        'phases': _merge_compatibility_phases(plan['phases']),
        'bcp_envelopes': plan['bcp_envelopes'],
        'selected_primitives': plan['selected_primitives'],
        'confusion_margins': plan['confusion_margins'],
        'rejected_candidates': plan['rejected_candidates'],
        'compiled_config': plan['compiled_config'],
    }



def compile_behavior_unit_to_sequence(behavior_unit: dict):
    """Compile a legacy behavior unit by returning its runtime-ready config."""
    return dict(behavior_unit['compiled_config'])




def build_emotion_configs(top_k: int = 1, lambda_weight: float = 1.0, rho: float = 0.5):
    """Build runtime configs for all supported emotions.

    ``top_k`` is retained only for backward-compatible signature stability. The
    façade always compiles the single planner-selected behavior plan per emotion.
    """
    _ = top_k
    return {
        emotion: build_behavior_plan(emotion, rho=rho, lambda_weight=lambda_weight)['compiled_config']
        for emotion in SUPPORTED_EMOTIONS
    }


__all__ = [
    'NEUTRAL_PAD',
    'PAD_ANCHORS',
    'compute_target_state',
    'update_affective_state',
    'state_to_bcp',
    'rollout_affective_episode',
    'trajectory_to_bcp_envelopes',
    'select_behavior_plan',
    'build_behavior_plan',
    'build_behavior_unit',
    'compile_behavior_plan_to_sequence',
    'compile_behavior_unit_to_sequence',
    'build_emotion_configs',
]
