"""Map affective PAD episode phases onto paper-facing BCP envelopes."""

PHASE_ORDER = [
    'neutral_hold',
    'ramp_up',
    'expressive_peak',
    'decay',
    'return_to_neutral',
]

EMOTION_BASELINE_BCP = {
    'happy': {'directionality': 'approach', 'posture_height': 'high', 'body_attitude': 'open', 'rhythm': 'buoyant'},
    'sad': {'directionality': 'withdraw', 'posture_height': 'low', 'body_attitude': 'droop', 'rhythm': 'sustained'},
    'fearful': {'directionality': 'retreat', 'posture_height': 'low', 'body_attitude': 'tense', 'rhythm': 'freeze'},
    'angry': {'directionality': 'approach', 'posture_height': 'high', 'body_attitude': 'tense', 'rhythm': 'driving'},
    'disgusted': {'directionality': 'avoid', 'posture_height': 'medium', 'body_attitude': 'stiff', 'rhythm': 'punctuated'},
    'surprised': {'directionality': 'orient', 'posture_height': 'high', 'body_attitude': 'alert', 'rhythm': 'punctuated'},
}

EMOTION_PHASE_PROTOTYPES = {
    'happy': {
        'neutral_hold': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.15),
            'rhythm': 'settled',
        },
        'ramp_up': {
            'directionality': 'approach',
            'posture_height': 'high',
            'body_attitude': 'open',
            'motion_speed': 'medium',
            'motion_energy': (0.2, 0.55),
            'rhythm': 'buoyant',
        },
        'expressive_peak': {
            'directionality': 'approach',
            'posture_height': 'high',
            'body_attitude': 'open',
            'motion_speed': 'high',
            'motion_energy': (0.55, 0.85),
            'rhythm': 'buoyant',
        },
        'decay': {
            'directionality': 'approach',
            'posture_height': 'medium',
            'body_attitude': 'open',
            'motion_speed': 'medium',
            'motion_energy': (0.25, 0.5),
            'rhythm': 'settled',
        },
        'return_to_neutral': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.25),
            'rhythm': 'settling',
        },
    },
    'sad': {
        'neutral_hold': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.1),
            'rhythm': 'settled',
        },
        'ramp_up': {
            'directionality': 'withdraw',
            'posture_height': 'low',
            'body_attitude': 'droop',
            'motion_speed': 'low',
            'motion_energy': (0.05, 0.2),
            'rhythm': 'sustained',
        },
        'expressive_peak': {
            'directionality': 'withdraw',
            'posture_height': 'low',
            'body_attitude': 'droop',
            'motion_speed': 'low',
            'motion_energy': (0.1, 0.25),
            'rhythm': 'sustained',
        },
        'decay': {
            'directionality': 'withdraw',
            'posture_height': 'low',
            'body_attitude': 'droop',
            'motion_speed': 'low',
            'motion_energy': (0.05, 0.2),
            'rhythm': 'sustained',
        },
        'return_to_neutral': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.15),
            'rhythm': 'settling',
        },
    },
    'fearful': {
        'neutral_hold': {
            'directionality': 'orient',
            'posture_height': 'medium',
            'body_attitude': 'tense',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.15),
            'rhythm': 'freeze',
        },
        'ramp_up': {
            'directionality': 'orient',
            'posture_height': 'low',
            'body_attitude': 'tense',
            'motion_speed': 'medium',
            'motion_energy': (0.15, 0.45),
            'rhythm': 'freeze',
        },
        'expressive_peak': {
            'directionality': 'retreat',
            'posture_height': 'low',
            'body_attitude': 'tense',
            'motion_speed': 'medium',
            'motion_energy': (0.3, 0.75),
            'rhythm': 'freeze',
        },
        'decay': {
            'directionality': 'retreat',
            'posture_height': 'low',
            'body_attitude': 'guarded',
            'motion_speed': 'low',
            'motion_energy': (0.15, 0.4),
            'rhythm': 'sustained',
        },
        'return_to_neutral': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.2),
            'rhythm': 'settling',
        },
    },
    'angry': {
        'neutral_hold': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.15),
            'rhythm': 'settled',
        },
        'ramp_up': {
            'directionality': 'approach',
            'posture_height': 'high',
            'body_attitude': 'tense',
            'motion_speed': 'medium',
            'motion_energy': (0.25, 0.55),
            'rhythm': 'driving',
        },
        'expressive_peak': {
            'directionality': 'approach',
            'posture_height': 'high',
            'body_attitude': 'tense',
            'motion_speed': 'high',
            'motion_energy': (0.5, 0.85),
            'rhythm': 'driving',
        },
        'decay': {
            'directionality': 'approach',
            'posture_height': 'medium',
            'body_attitude': 'tense',
            'motion_speed': 'medium',
            'motion_energy': (0.25, 0.5),
            'rhythm': 'sustained',
        },
        'return_to_neutral': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.2),
            'rhythm': 'settling',
        },
    },
    'disgusted': {
        'neutral_hold': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.1),
            'rhythm': 'settled',
        },
        'ramp_up': {
            'directionality': 'avoid',
            'posture_height': 'medium',
            'body_attitude': 'stiff',
            'motion_speed': 'low',
            'motion_energy': (0.1, 0.3),
            'rhythm': 'punctuated',
        },
        'expressive_peak': {
            'directionality': 'avoid',
            'posture_height': 'medium',
            'body_attitude': 'stiff',
            'motion_speed': 'medium',
            'motion_energy': (0.2, 0.45),
            'rhythm': 'punctuated',
        },
        'decay': {
            'directionality': 'avoid',
            'posture_height': 'medium',
            'body_attitude': 'stiff',
            'motion_speed': 'low',
            'motion_energy': (0.1, 0.25),
            'rhythm': 'sustained',
        },
        'return_to_neutral': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.15),
            'rhythm': 'settling',
        },
    },
    'surprised': {
        'neutral_hold': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.15),
            'rhythm': 'settled',
        },
        'ramp_up': {
            'directionality': 'orient',
            'posture_height': 'high',
            'body_attitude': 'alert',
            'motion_speed': 'high',
            'motion_energy': (0.3, 0.65),
            'rhythm': 'punctuated',
        },
        'expressive_peak': {
            'directionality': 'orient',
            'posture_height': 'high',
            'body_attitude': 'alert',
            'motion_speed': 'high',
            'motion_energy': (0.45, 0.8),
            'rhythm': 'punctuated',
        },
        'decay': {
            'directionality': 'orient',
            'posture_height': 'medium',
            'body_attitude': 'alert',
            'motion_speed': 'medium',
            'motion_energy': (0.2, 0.45),
            'rhythm': 'sustained',
        },
        'return_to_neutral': {
            'directionality': 'neutral',
            'posture_height': 'medium',
            'body_attitude': 'steady',
            'motion_speed': 'low',
            'motion_energy': (0.0, 0.2),
            'rhythm': 'settling',
        },
    },
}


def _clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, value))


def _energy_bounds(states, prototype_bounds):
    arousal_values = [state[1] for state in states]
    if not arousal_values:
        return {'lower': prototype_bounds[0], 'upper': prototype_bounds[1]}

    lower = min(prototype_bounds[0], _clamp(min(arousal_values)))
    upper = max(prototype_bounds[1], _clamp(max(arousal_values)))
    return {'lower': lower, 'upper': upper}


def _validate_state_tuple(state, context):
    if not isinstance(state, (list, tuple)) or len(state) != 3:
        raise ValueError(f'{context} must be a 3-value PAD state, got {state!r}')
    return tuple(state)


def _phase_states(phase_name, phase):
    states = phase.get('states')
    if not isinstance(states, list):
        raise ValueError(f'phase {phase_name} has malformed states: expected list')

    source_states = []
    for point in states:
        if not isinstance(point, dict) or 'state' not in point:
            raise ValueError(f'phase {phase_name} has malformed states: each entry must include state')
        _validate_state_tuple(point['state'], f'phase {phase_name} state')
        source_states.append(point['state'])
    return source_states


def _validate_episode_phases(episode):
    phases = episode.get('phases')
    if not isinstance(phases, list):
        raise ValueError("episode must include a 'phases' list")

    phase_map = {}
    for phase in phases:
        if not isinstance(phase, dict) or not isinstance(phase.get('name'), str):
            raise ValueError("episode phases must be dicts with a string 'name'")
        phase_map[phase['name']] = phase

    for phase_name in PHASE_ORDER:
        if phase_name not in phase_map:
            raise ValueError(f'missing required phase: {phase_name}')

    return phase_map


def state_to_bcp(emotion: str, state):
    pleasure, arousal, dominance = _validate_state_tuple(state, 'state')
    baseline = EMOTION_BASELINE_BCP[emotion]

    directionality = baseline['directionality']
    if pleasure < -0.2:
        directionality = 'retreat'
    elif pleasure > 0.2:
        directionality = baseline['directionality']
    elif abs(pleasure) <= 0.1 and baseline['directionality'] in {'approach', 'retreat', 'avoid', 'orient'}:
        directionality = 'neutral'

    posture_height = baseline['posture_height']
    if pleasure < -0.3:
        posture_height = 'low'
    elif pleasure > 0.3:
        posture_height = baseline['posture_height']
    elif abs(pleasure) <= 0.1:
        posture_height = 'medium'

    body_attitude = baseline['body_attitude']
    if dominance < -0.2:
        body_attitude = 'tense'
    elif dominance > 0.2:
        body_attitude = 'open' if baseline['body_attitude'] in {'open', 'steady'} else baseline['body_attitude']
    elif abs(dominance) <= 0.1:
        body_attitude = 'steady'

    return {
        'directionality': directionality,
        'posture_height': posture_height,
        'body_attitude': body_attitude,
        'motion_speed': 'high' if arousal > 0.6 else 'medium' if arousal > 0.2 else 'low',
        'motion_energy': 'high' if arousal > 0.6 else 'medium' if arousal > 0.2 else 'low',
        'rhythm': baseline['rhythm'] if arousal > 0.2 else 'settled',
    }


def trajectory_to_bcp_envelopes(emotion: str, episode: dict):
    prototypes = EMOTION_PHASE_PROTOTYPES[emotion]
    phase_map = _validate_episode_phases(episode)
    envelopes = []

    for phase_name in PHASE_ORDER:
        phase = phase_map[phase_name]
        prototype = prototypes[phase_name]
        source_states = _phase_states(phase_name, phase)
        envelopes.append(
            {
                'phase': phase_name,
                'directionality': {'preferred': prototype['directionality']},
                'posture_height': {'preferred': prototype['posture_height']},
                'body_attitude': {'preferred': prototype['body_attitude']},
                'motion_speed': {'preferred': prototype['motion_speed']},
                'motion_energy': _energy_bounds(source_states, prototype['motion_energy']),
                'rhythm': {'preferred': prototype['rhythm']},
                'source_states': source_states,
            }
        )

    return envelopes
