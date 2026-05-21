"""Utilities for rolling out five-phase affective PAD episodes.

Public API:
- compute_target_state(emotion, rho) -> [P, A, D]
- update_affective_state(current_state, target_state, dt=0.1, kappa=1.0) -> [P, A, D]
- rollout_affective_episode(...) -> {
    'emotion': str,
    'rho': float,
    'target_state': [P, A, D],
    'phases': [
        {
            'name': str,
            'kappa': float,
            'target': [P, A, D],
            'states': [{'phase': str, 'state': [P, A, D]}, ...],
        },
        ...,
    ],
    'trajectory': [{'phase': str, 'state': [P, A, D]}, ...],
}
"""

EPISODE_PHASES = [
    {'name': 'neutral_hold', 'kappa': 0.0, 'target': 'neutral'},
    {'name': 'ramp_up', 'kappa': 1.0, 'target': 'emotion_target'},
    {'name': 'expressive_peak', 'kappa': 0.0, 'target': 'emotion_target'},
    {'name': 'decay', 'kappa': 1.0, 'target': 'mid_decay'},
    {'name': 'return_to_neutral', 'kappa': 1.0, 'target': 'neutral'},
]

PHASE_STEP_DEFAULTS = {
    'neutral_hold': {'steps': 0, 'include_start': True},
    'ramp_up': {'steps': 'ramp_steps', 'include_start': False},
    'expressive_peak': {'steps': 0, 'include_start': True},
    'decay': {'steps': 'match_ramp', 'include_start': True},
    'return_to_neutral': {'steps': 'double_ramp_min_three', 'include_start': True},
}

NEUTRAL_PAD = [0.0, 0.0, 0.0]

PAD_ANCHORS = {
    'happy': [0.76, 0.48, 0.35],
    'sad': [-0.63, -0.27, -0.33],
    'fearful': [-0.64, 0.6, -0.43],
    'angry': [-0.51, 0.59, 0.25],
    'disgusted': [-0.6, 0.35, 0.11],
    'surprised': [0.4, 0.67, -0.13],
}


def _clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, value))


def _interpolate(start, end, alpha):
    return [start[i] + (end[i] - start[i]) * alpha for i in range(3)]


def compute_target_state(emotion, rho):
    """Return the PAD target for ``emotion`` at clamped intensity ``rho``."""
    if emotion not in PAD_ANCHORS:
        raise ValueError(f'Unknown emotion: {emotion}')
    alpha = _clamp(rho)
    return _interpolate(NEUTRAL_PAD, PAD_ANCHORS[emotion], alpha)


def update_affective_state(current_state, target_state, dt=0.1, kappa=1.0):
    """Move one step toward ``target_state`` with clamped smoothing alpha ``dt * kappa``."""
    alpha = _clamp(dt * kappa)
    return _interpolate(current_state, target_state, alpha)


def _capture_state(trajectory, phase_name, state):
    point = {'phase': phase_name, 'state': list(state)}
    trajectory.append(point)
    return point


def _build_phase(phase_template, starting_state, phase_target, steps, dt, phase_kappa, trajectory, include_start=False):
    current_state = list(starting_state)
    phase = dict(phase_template)
    phase['kappa'] = phase_kappa
    phase['target'] = list(phase_target)
    phase['states'] = []

    if include_start or steps <= 0:
        phase['states'].append(_capture_state(trajectory, phase['name'], current_state))

    for _ in range(steps):
        current_state = update_affective_state(
            current_state,
            phase_target,
            dt=dt,
            kappa=phase_kappa,
        )
        phase['states'].append(_capture_state(trajectory, phase['name'], current_state))

    if not phase['states']:
        phase['states'].append(_capture_state(trajectory, phase['name'], current_state))

    return phase, current_state


def _resolve_step_value(step_policy, ramp_steps):
    if isinstance(step_policy, int):
        return step_policy
    if step_policy == 'ramp_steps':
        return max(0, ramp_steps)
    if step_policy == 'match_ramp':
        return max(1, ramp_steps)
    if step_policy == 'double_ramp_min_three':
        return max(3, ramp_steps * 2)
    raise ValueError(f'Unknown phase step policy: {step_policy}')


def _resolve_phase_steps(ramp_steps):
    return {
        phase_name: _resolve_step_value(policy['steps'], ramp_steps)
        for phase_name, policy in PHASE_STEP_DEFAULTS.items()
    }


def rollout_affective_episode(emotion, rho, dt=1.0, kappa=0.6, ramp_steps=3):
    target_state = compute_target_state(emotion, rho)
    decay_state = _interpolate(target_state, NEUTRAL_PAD, 0.5)
    resolved_targets = {
        'neutral': list(NEUTRAL_PAD),
        'emotion_target': list(target_state),
        'mid_decay': list(decay_state),
    }
    phase_steps = _resolve_phase_steps(ramp_steps)
    trajectory = []
    phases = []
    current_state = list(NEUTRAL_PAD)

    for phase_template in EPISODE_PHASES:
        phase_name = phase_template['name']
        policy = PHASE_STEP_DEFAULTS[phase_name]
        phase_target = resolved_targets[phase_template['target']]
        phase_kappa = 0.0 if phase_name in ('neutral_hold', 'expressive_peak') else kappa
        phase, current_state = _build_phase(
            phase_template=phase_template,
            starting_state=current_state,
            phase_target=phase_target,
            steps=phase_steps[phase_name],
            dt=dt,
            phase_kappa=phase_kappa,
            trajectory=trajectory,
            include_start=policy['include_start'],
        )
        phases.append(phase)

    return {
        'emotion': emotion,
        'rho': rho,
        'target_state': target_state,
        'phases': phases,
        'trajectory': trajectory,
    }
