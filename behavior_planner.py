"""Primitive behavior planning from phase-wise BCP envelopes."""

from typing import Any, Dict, Iterable, List, Optional, Set, TypedDict


class BehaviorPlanDict(TypedDict):
    selected_primitives: List[Dict[str, Any]]
    confusion_margins: List[Dict[str, Any]]
    rejected_candidates: List[Dict[str, Any]]


class PhaseSelectionReportDict(TypedDict):
    phase: str
    emotion: str
    beam_winner: str
    selected_primitive: str
    selected_score: float
    selected_candidate: Dict[str, Any]
    phase_candidates: List[Dict[str, Any]]
    rejections: List[Dict[str, Any]]


class PhaseCandidateRecordDict(TypedDict):
    primitive: str
    phase: str
    emotion: str
    score: float
    match_score: float
    phase_bias: float
    temporal_bonus: float
    emotion_signal_bonus: float
    emotion_signal_component: float
    confusion_penalty: float
    component_scores: Dict[str, float]
    selected: bool
    lost_to: Optional[str]
    score_gap: float
    candidate_labels: Dict[str, Any]
    candidate: Dict[str, Any]


class ScoredCandidateDict(TypedDict):
    primitive: str
    score: float
    match_score: float
    phase_bias: float
    temporal_bonus: float
    emotion_signal_bonus: float
    emotion_signal_component: float
    confusion_penalty: float
    component_scores: Dict[str, float]
    candidate: Dict[str, Any]


class PrimitiveCandidateDict(TypedDict):
    primitive: str
    phase: str
    emotion: str
    labels: Dict[str, Any]
    phase_bias: float
    recovery_tags: Set[str]
    match_score: float
    emotion_signal_score: float
    emotion_signal_bonus: float


class EnvelopeDict(TypedDict, total=False):
    phase: str
    directionality: Dict[str, Any]
    posture_height: Dict[str, Any]
    body_attitude: Dict[str, Any]
    motion_speed: Dict[str, Any]
    rhythm: Dict[str, Any]


class BeamEntryDict(TypedDict):
    selected_primitives: List[Dict[str, Any]]
    score: float
    confusion_margins: List[Dict[str, Any]]
    rejected_candidates: List[Dict[str, Any]]


PREFERRED_VALUE_KEY = 'preferred'


def _preferred_label_value(envelope, key):
    value = envelope.get(key)
    if isinstance(value, dict):
        return value.get(PREFERRED_VALUE_KEY)
    return value


PrimitiveCandidate = PrimitiveCandidateDict
ScoredCandidate = ScoredCandidateDict
PhaseCandidateRecord = PhaseCandidateRecordDict
PhaseSelectionReport = PhaseSelectionReportDict
BehaviorPlan = BehaviorPlanDict
Envelope = EnvelopeDict
BeamEntry = BeamEntryDict


PRIMITIVE_LIBRARY = {
    'orient': {
        'labels': {
            'directionality': 'orient',
            'posture_height': 'medium',
            'body_attitude': 'alert',
            'motion_speed': 'medium',
            'rhythm': 'punctuated',
        },
        'phase_biases': {'neutral_hold': 0.1, 'ramp_up': 0.25, 'expressive_peak': 0.1},
        'recovery_tags': {'attention'},
    },
    'advance': {
        'labels': {
            'directionality': 'approach',
            'posture_height': 'high',
            'body_attitude': 'open',
            'motion_speed': 'medium',
            'rhythm': 'buoyant',
        },
        'phase_biases': {'ramp_up': 0.3, 'expressive_peak': 0.2, 'decay': 0.1},
        'recovery_tags': {'locomotion'},
    },
    'retreat': {
        'labels': {
            'directionality': 'retreat',
            'posture_height': 'low',
            'body_attitude': 'tense',
            'motion_speed': 'medium',
            'rhythm': 'freeze',
        },
        'phase_biases': {'ramp_up': 0.1, 'expressive_peak': 0.35, 'decay': 0.15},
        'recovery_tags': {'locomotion', 'defensive'},
    },
    'freeze': {
        'labels': {
            'directionality': 'orient',
            'posture_height': 'low',
            'body_attitude': 'tense',
            'motion_speed': 'low',
            'rhythm': 'freeze',
        },
        'phase_biases': {'neutral_hold': 0.2, 'ramp_up': 0.2, 'expressive_peak': 0.4, 'decay': 0.15},
        'recovery_tags': {'defensive', 'stability'},
    },
    'lower_body': {
        'labels': {
            'directionality': 'neutral',
            'posture_height': 'low',
            'body_attitude': 'droop',
            'motion_speed': 'low',
            'rhythm': 'sustained',
        },
        'phase_biases': {'ramp_up': 0.2, 'expressive_peak': 0.2, 'decay': 0.25},
        'recovery_tags': {'posture'},
    },
    'raise_body': {
        'labels': {
            'directionality': 'neutral',
            'posture_height': 'high',
            'body_attitude': 'alert',
            'motion_speed': 'medium',
            'rhythm': 'punctuated',
        },
        'phase_biases': {'ramp_up': 0.25, 'expressive_peak': 0.2},
        'recovery_tags': {'posture', 'attention'},
    },
    'oscillate': {
        'labels': {
            'directionality': 'approach',
            'posture_height': 'high',
            'body_attitude': 'open',
            'motion_speed': 'high',
            'rhythm': 'buoyant',
        },
        'phase_biases': {'expressive_peak': 0.35, 'decay': 0.15},
        'recovery_tags': {'expressive'},
    },
    'stiffen': {
        'labels': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'stiff',
            'motion_speed': 'low',
            'rhythm': 'punctuated',
        },
        'phase_biases': {'ramp_up': 0.1, 'expressive_peak': 0.2, 'decay': 0.2},
        'recovery_tags': {'stability'},
    },
    'recovery_stand': {
        'labels': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'rhythm': 'settling',
        },
        'phase_biases': {'return_to_neutral': 0.5, 'decay': 0.2},
        'recovery_tags': {'stability', 'posture'},
    },
}

CONFUSION_PROTOTYPE_GROUPS = {
    'withdrawn_defensive': {
        'prototype': {
            'directionality': 'retreat',
            'posture_height': 'low',
            'body_attitude': 'tense',
            'rhythm': 'freeze',
        },
        'applies_to': {'happy', 'angry', 'disgusted'},
        'rationale': 'Discourage collapse into defensive withdrawal when a more distinct affect should read through.',
    },
    'settled_neutral': {
        'prototype': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'rhythm': 'settling',
        },
        'applies_to': {'sad'},
        'rationale': 'Discourage overly neutral recovery-like behavior during active sad expression phases.',
    },
    'buoyant_approach': {
        'prototype': {
            'directionality': 'approach',
            'posture_height': 'high',
            'body_attitude': 'open',
            'rhythm': 'buoyant',
        },
        'applies_to': {'fearful', 'surprised'},
        'rationale': 'Discourage positive/approach-like readouts when the target emotion should not resolve as playful confidence.',
    },
}

CONFUSION_PROTOTYPES = {
    emotion: dict(group['prototype'])
    for group in CONFUSION_PROTOTYPE_GROUPS.values()
    for emotion in group['applies_to']
}

EMOTION_PRIMITIVE_PRIORS = {
    'happy': {'advance': 1.0, 'oscillate': 1.0, 'raise_body': 0.5, 'orient': 0.25},
    'sad': {'lower_body': 1.0, 'recovery_stand': 0.75, 'freeze': 0.25},
    'fearful': {'freeze': 1.0, 'retreat': 1.0, 'orient': 0.5, 'stiffen': 0.5},
    'angry': {'stiffen': 1.0, 'raise_body': 0.75, 'orient': 0.5, 'advance': 0.25},
    'disgusted': {'retreat': 1.0, 'lower_body': 0.5, 'stiffen': 0.5},
    'surprised': {'orient': 1.0, 'raise_body': 0.75, 'freeze': 0.5, 'advance': 0.25},
}

EMOTION_SIGNAL_FIELDS = ('directionality', 'posture_height', 'body_attitude', 'rhythm')
EMOTION_SIGNAL_WEIGHT = 5.5
EMOTION_SIGNAL_BONUS_SCALE = 0.05

RECOVERY_COMPATIBILITY = {
    'recovery_stand': {'recovery_stand': 0.3, 'freeze': 0.2, 'stiffen': 0.2, 'lower_body': 0.1},
    'freeze': {'retreat': 0.2, 'freeze': 0.3, 'recovery_stand': 0.2},
    'retreat': {'freeze': 0.2, 'recovery_stand': 0.1},
    'advance': {'oscillate': 0.15, 'recovery_stand': 0.1},
    'orient': {'freeze': 0.15, 'raise_body': 0.1},
}

MATCH_FIELDS = ('directionality', 'posture_height', 'body_attitude', 'motion_speed', 'rhythm')
SUPPORTED_EMOTIONS = frozenset(CONFUSION_PROTOTYPES)

PRIMITIVE_STEP_TEMPLATES = {
    'orient': {
        'mode': 21,
        'gait_id': 0,
        'velocity': [0.0, 0.0, 0.0],
        'step_height': [0.03, 0.03],
        'body_height': 0.23,
        'position': [0.0, 0.0, 0.0],
        'rpy': [0.0, 0.08, 0.3],
        'duration': 350,
    },
    'advance': {
        'mode': 11,
        'gait_id': 10,
        'velocity': [0.22, 0.0, 0.0],
        'step_height': [0.04, 0.04],
        'body_height': 0.245,
        'position': [0.0, 0.0, 0.0],
        'rpy': [0.0, 0.0, 0.0],
        'duration': 320,
    },
    'retreat': {
        'mode': 11,
        'gait_id': 27,
        'velocity': [-0.18, 0.0, 0.0],
        'step_height': [0.025, 0.025],
        'body_height': 0.2,
        'position': [0.0, 0.0, 0.0],
        'rpy': [0.0, -0.08, 0.0],
        'duration': 360,
    },
    'freeze': {
        'mode': 12,
        'gait_id': 0,
        'velocity': [0.0, 0.0, 0.0],
        'step_height': [0.02, 0.02],
        'body_height': 0.2,
        'position': [0.0, 0.0, 0.0],
        'rpy': [0.0, -0.08, 0.0],
        'duration': 420,
    },
    'lower_body': {
        'mode': 21,
        'gait_id': 5,
        'velocity': [0.0, 0.0, 0.0],
        'step_height': [0.02, 0.02],
        'body_height': 0.2,
        'position': [0.0, 0.0, 0.0],
        'rpy': [0.0, -0.12, 0.0],
        'duration': 420,
    },
    'raise_body': {
        'mode': 21,
        'gait_id': 5,
        'velocity': [0.0, 0.0, 0.0],
        'step_height': [0.04, 0.04],
        'body_height': 0.25,
        'position': [0.0, 0.0, 0.0],
        'rpy': [0.0, 0.06, 0.0],
        'duration': 320,
    },
    'oscillate': {
        'mode': 11,
        'gait_id': 10,
        'velocity': [0.25, 0.0, 0.0],
        'step_height': [0.05, 0.05],
        'body_height': 0.25,
        'position': [0.0, 0.0, 0.0],
        'rpy': [0.0, 0.1, 0.0],
        'duration': 260,
    },
    'stiffen': {
        'mode': 21,
        'gait_id': 0,
        'velocity': [0.0, 0.0, 0.0],
        'step_height': [0.025, 0.025],
        'body_height': 0.23,
        'position': [0.02, 0.0, 0.0],
        'rpy': [0.0, -0.12, 0.0],
        'duration': 320,
    },
    'recovery_stand': {
        'mode': 3,
        'gait_id': 0,
        'velocity': [0.0, 0.0, 0.0],
        'step_height': [0.03, 0.03],
        'body_height': 0.23,
        'position': [0.0, 0.0, 0.0],
        'rpy': [0.0, 0.0, 0.0],
        'duration': 500,
    },
}

EMOTION_RUNTIME_DEFAULTS = {
    'happy': {'type': 'loop', 'demo_seconds_min': 2.0},
    'sad': {'type': 'single', 'demo_seconds_min': 1.5},
    'fearful': {'type': 'single', 'demo_seconds_min': 1.5},
    'angry': {'type': 'single', 'demo_seconds_min': 1.5},
    'disgusted': {'type': 'single', 'demo_seconds_min': 1.5},
    'surprised': {'type': 'single', 'demo_seconds_min': 1.0},
}


def _validate_supported_emotion(emotion: str):
    if emotion not in SUPPORTED_EMOTIONS:
        supported = ', '.join(sorted(SUPPORTED_EMOTIONS))
        raise ValueError(f"Unsupported emotion '{emotion}'. Supported emotions: {supported}")
    return emotion


def _label_match_score(envelope, labels):
    score = 0.0
    for field in MATCH_FIELDS:
        preferred = _preferred_label_value(envelope, field)
        if preferred is not None and labels.get(field) == preferred:
            score += 1.0
    return score


def _emotion_signal_score(emotion, labels):
    prototype = CONFUSION_PROTOTYPES[_validate_supported_emotion(emotion)]
    signal_score = 0.0
    for field in EMOTION_SIGNAL_FIELDS:
        if labels.get(field) != prototype.get(field):
            signal_score += 1.0
    signal_score += EMOTION_PRIMITIVE_PRIORS.get(emotion, {}).get(labels.get('primitive_name'), 0.0)
    return signal_score


def _emotion_signal_bonus(emotion, labels):
    return EMOTION_SIGNAL_BONUS_SCALE * _emotion_signal_score(emotion, labels)


def _emotion_signal_component(emotion, labels):
    return EMOTION_SIGNAL_WEIGHT * _emotion_signal_bonus(emotion, labels)


def _confusion_penalty(emotion, labels):
    prototype = CONFUSION_PROTOTYPES[_validate_supported_emotion(emotion)]
    penalty = 0.0
    for field, confusing_value in prototype.items():
        if labels.get(field) == confusing_value:
            penalty += 1.0
    return penalty


def _temporal_consistency(previous_candidate, candidate):
    if not previous_candidate:
        return 0.0

    bonus = 0.0
    previous_primitive = previous_candidate['primitive']
    current_primitive = candidate['primitive']
    if previous_primitive == current_primitive:
        bonus += 0.2
    bonus += RECOVERY_COMPATIBILITY.get(previous_primitive, {}).get(current_primitive, 0.0)
    if previous_candidate.get('recovery_tags', set()) & candidate.get('recovery_tags', set()):
        bonus += 0.1
    return bonus


def _sort_candidate_key(candidate: PrimitiveCandidate):
    return (
        candidate['match_score'],
        candidate['phase_bias'],
        candidate['emotion_signal_bonus'],
        candidate['emotion_signal_score'],
    )


def _build_phase_candidate(emotion: str, phase_name: str, primitive_name: str, primitive: dict, envelope: Envelope) -> PrimitiveCandidate:
    labels = dict(primitive['labels'])
    labels['primitive_name'] = primitive_name
    match_score = _label_match_score(envelope, labels)
    emotion_signal_score = _emotion_signal_score(emotion, labels)
    emotion_signal_bonus = _emotion_signal_bonus(emotion, labels)
    return {
        'primitive': primitive_name,
        'phase': phase_name,
        'emotion': emotion,
        'labels': labels,
        'phase_bias': primitive.get('phase_biases', {}).get(phase_name, 0.0),
        'recovery_tags': set(primitive.get('recovery_tags', set())),
        'match_score': match_score,
        'emotion_signal_score': emotion_signal_score,
        'emotion_signal_bonus': emotion_signal_bonus,
    }


def generate_phase_candidates(emotion: str, envelope: Envelope) -> List[PrimitiveCandidate]:
    """Return phase-matched primitive candidates sorted by local desirability."""
    emotion = _validate_supported_emotion(emotion)
    phase_name = envelope['phase']
    candidates = []
    for primitive_name, primitive in PRIMITIVE_LIBRARY.items():
        candidate = _build_phase_candidate(emotion, phase_name, primitive_name, primitive, envelope)
        if candidate['match_score'] >= 2:
            candidates.append(candidate)

    candidates.sort(key=_sort_candidate_key, reverse=True)
    return candidates


def score_primitive_candidate(
    emotion: str,
    envelope: Envelope,
    candidate: PrimitiveCandidate,
    previous_candidate: Optional[PrimitiveCandidate] = None,
    lambda_weight: float = 1.0,
) -> ScoredCandidate:
    """Score one primitive candidate against the current phase envelope.

    Returns a dict with the total score, named score components, and the original
    candidate under ``candidate`` for downstream beam selection/reporting.
    """
    emotion = _validate_supported_emotion(emotion)
    candidate_labels = candidate['labels']
    match_score = _label_match_score(envelope, candidate_labels)
    phase_bias = candidate.get('phase_bias', 0.0)
    emotion_signal_bonus = candidate.get('emotion_signal_bonus', _emotion_signal_bonus(emotion, candidate_labels))
    confusion_penalty = _confusion_penalty(emotion, candidate_labels)
    temporal_bonus = _temporal_consistency(previous_candidate, candidate)
    emotion_signal_component = _emotion_signal_component(emotion, candidate_labels)
    score = match_score + phase_bias + temporal_bonus + emotion_signal_component - (lambda_weight * confusion_penalty)
    component_scores = {
        'match_score': match_score,
        'phase_bias': phase_bias,
        'temporal_bonus': temporal_bonus,
        'emotion_signal_bonus': emotion_signal_bonus,
        'emotion_signal_component': emotion_signal_component,
        'confusion_penalty': confusion_penalty,
    }
    return {
        'primitive': candidate['primitive'],
        'score': score,
        'match_score': match_score,
        'phase_bias': phase_bias,
        'temporal_bonus': temporal_bonus,
        'emotion_signal_bonus': emotion_signal_bonus,
        'emotion_signal_component': emotion_signal_component,
        'confusion_penalty': confusion_penalty,
        'component_scores': component_scores,
        'candidate': candidate,
    }


def _phase_candidate_record(
    scored_item: ScoredCandidate,
    phase: str,
    emotion: str,
    selected_primitive: str,
    selected_score: float,
    selected: bool,
) -> PhaseCandidateRecord:
    """Shape one scored candidate into the public per-phase diagnostic record."""
    return {
        'primitive': scored_item['primitive'],
        'phase': phase,
        'emotion': emotion,
        'score': scored_item['score'],
        'match_score': scored_item['match_score'],
        'phase_bias': scored_item['phase_bias'],
        'temporal_bonus': scored_item['temporal_bonus'],
        'emotion_signal_bonus': scored_item['emotion_signal_bonus'],
        'emotion_signal_component': scored_item['emotion_signal_component'],
        'confusion_penalty': scored_item['confusion_penalty'],
        'component_scores': dict(scored_item['component_scores']),
        'selected': selected,
        'lost_to': None if selected else selected_primitive,
        'score_gap': 0.0 if selected else selected_score - scored_item['score'],
        'candidate_labels': scored_item['candidate']['labels'],
        'candidate': scored_item['candidate'],
    }


def _margin_against_competitors(scored_item: ScoredCandidate, scored_candidates: Iterable[ScoredCandidate]) -> float:
    competing_scores = [item['score'] for item in scored_candidates if item['primitive'] != scored_item['primitive']]
    return scored_item['score'] - max(competing_scores) if competing_scores else scored_item['score']


def _build_phase_candidates_report(
    scored_candidates: List[ScoredCandidate],
    phase: str,
    emotion: str,
    selected_item: ScoredCandidate,
) -> List[PhaseCandidateRecord]:
    return [
        _phase_candidate_record(
            item,
            phase,
            emotion,
            selected_item['primitive'],
            selected_item['score'],
            selected=(item['primitive'] == selected_item['primitive']),
        )
        for item in scored_candidates
    ]


def _build_phase_selection_report(
    phase: str,
    emotion: str,
    selected_item: ScoredCandidate,
    phase_candidates: List[PhaseCandidateRecord],
) -> PhaseSelectionReport:
    """Return the public nested report for one selected beam branch phase."""
    return {
        'phase': phase,
        'emotion': emotion,
        'beam_winner': selected_item['primitive'],
        'selected_primitive': selected_item['primitive'],
        'selected_score': selected_item['score'],
        'selected_candidate': selected_item['candidate'],
        'phase_candidates': phase_candidates,
        'rejections': phase_candidates[1:],
    }


def _expand_partial_plan(
    partial_plan: Dict[str, Any],
    emotion: str,
    envelope: Envelope,
    lambda_weight: float,
    beam_width: int,
) -> List[Dict[str, Any]]:
    previous_candidate = partial_plan['selected_primitives'][-1] if partial_plan['selected_primitives'] else None
    scored_candidates = [
        score_primitive_candidate(
            emotion,
            envelope,
            candidate,
            previous_candidate=previous_candidate,
            lambda_weight=lambda_weight,
        )
        for candidate in generate_phase_candidates(emotion, envelope)
    ]
    scored_candidates.sort(key=lambda item: item['score'], reverse=True)
    if not scored_candidates:
        return []

    expanded_plans = []
    for scored in scored_candidates[: max(1, beam_width)]:
        margin = _margin_against_competitors(scored, scored_candidates)
        phase_candidates = _build_phase_candidates_report(scored_candidates, envelope['phase'], emotion, scored)
        rejected = _build_phase_selection_report(envelope['phase'], emotion, scored, phase_candidates)
        expanded_plans.append(
            {
                'selected_primitives': partial_plan['selected_primitives'] + [scored['candidate']],
                'score': partial_plan['score'] + scored['score'],
                'confusion_margins': partial_plan['confusion_margins']
                + [
                    {
                        'phase': envelope['phase'],
                        'margin': margin,
                        'selected_primitive': scored['primitive'],
                    }
                ],
                'rejected_candidates': partial_plan['rejected_candidates'] + [rejected],
            }
        )
    return expanded_plans


def _copy_runtime_step(step: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: list(value) if isinstance(value, list) else value
        for key, value in step.items()
    }


def compile_behavior_plan_to_sequence(
    emotion: str,
    primitive_plan: Dict[str, Any],
) -> Dict[str, Any]:
    """Compile planner-selected primitives into runtime motion steps."""
    emotion = _validate_supported_emotion(emotion)
    selected_primitives = list(primitive_plan.get('selected_primitives', []))
    sequence = []
    for selected_primitive in selected_primitives:
        primitive_name = selected_primitive['primitive']
        try:
            template = PRIMITIVE_STEP_TEMPLATES[primitive_name]
        except KeyError as exc:
            raise ValueError(f'Unsupported primitive in behavior plan: {primitive_name}') from exc
        sequence.append(_copy_runtime_step(template))

    runtime_defaults = EMOTION_RUNTIME_DEFAULTS[emotion]
    total_duration_seconds = sum(step['duration'] for step in sequence) / 1000.0
    return {
        'type': runtime_defaults['type'],
        'demo_seconds': max(total_duration_seconds, runtime_defaults['demo_seconds_min']),
        'sequence': sequence,
    }


def select_behavior_plan(
    emotion: str,
    envelopes: Iterable[Envelope],
    lambda_weight: float = 1.0,
    beam_width: int = 2,
) -> BehaviorPlan:
    """Select a primitive sequence and expose beam diagnostics per phase.

    The returned dict contains ``selected_primitives``, ``confusion_margins``,
    and ``rejected_candidates``. Each rejected-candidate entry stores the
    chosen branch plus ordered per-phase candidate diagnostics.
    """
    emotion = _validate_supported_emotion(emotion)
    beam = [{'selected_primitives': [], 'score': 0.0, 'confusion_margins': [], 'rejected_candidates': []}]

    for envelope in envelopes:
        next_beam = []
        for partial_plan in beam:
            next_beam.extend(
                _expand_partial_plan(partial_plan, emotion, envelope, lambda_weight, beam_width)
            )

        next_beam.sort(key=lambda item: item['score'], reverse=True)
        beam = next_beam[: max(1, beam_width)]

    best_plan = beam[0] if beam else {'selected_primitives': [], 'confusion_margins': [], 'rejected_candidates': []}
    return {
        'selected_primitives': best_plan['selected_primitives'],
        'confusion_margins': best_plan['confusion_margins'],
        'rejected_candidates': best_plan['rejected_candidates'],
    }
