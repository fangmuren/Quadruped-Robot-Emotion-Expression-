"""Coarse keyword buckets for lightweight Chapter 4 feedback coding."""

THEME_KEYWORDS = {
    'directionality': ('前进', '前冲', '冲过来', '冲来', '靠近', '后退', '退后', '退缩'),
    'posture_height': ('压低', '低下', '抬高', '抬头', '趴低'),
    'body_attitude': ('蜷缩', '紧绷', '放松', '挺起', '侧身'),
    'motion_speed': ('很快', '快速', '飞快', '缓慢', '慢慢'),
    'motion_energy': ('有力', '用力', '猛烈', '轻轻', '轻柔'),
    'rhythm_flow': ('停住', '停下', '不动', '顿住'),
}


def detect_feedback_themes(text):
    detected = set()

    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            detected.add(theme)

    return detected


def summarize_feedback_themes(rows):
    summary = {theme: 0 for theme in THEME_KEYWORDS}

    for row in rows:
        for theme in detect_feedback_themes(row['text']):
            summary[theme] += 1

    return summary
