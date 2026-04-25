"""
六情绪动作参数配置（按接口表修正版）

说明：
1. 本文件保留原有高层字段命名：velocity / position / rpy / body_height / step_height。
2. 执行层需要做如下映射：
   - velocity    -> vel_des
   - position    -> pos_des（仅用于 mode=21, gait_id=0 的相对位姿）
   - rpy         -> rpy_des
   - body_height -> pos_des[2]
3. 依据接口表修正后的关键约束：
   - RECOVERY_STAND: mode=12, gait_id=0，duration 建议 >6000ms
   - POSE_CTRL 绝对姿态: mode=21, gait_id=5，仅用于站立高度
   - POSE_CTRL 相对姿态: mode=21, gait_id=0，用于机身 6 自由度相对位姿
   - LOCOMOTION 慢走: mode=11, gait_id=27
   - LOCOMOTION 小跑: mode=11, gait_id=10
   - MOTION 坐下: mode=62, gait_id=3
   - MOTION 扭屁股: mode=62, gait_id=4
"""

PDF_EMOTION_CONFIGS = {
    'happy': {
        'type': 'loop',
        'demo_seconds': 6.0,
        'sequence': [
            # 先恢复站立；接口表要求 duration > 6000ms
            {'mode': 12, 'gait_id': 0, 'duration': 6000},
            # 绝对站高
            {'mode': 21, 'gait_id': 5, 'body_height': 0.24, 'duration': 400},
            # 小跑点头：总时长 2500ms，拆成多个短 step 近似连续俯仰摆动
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, -0.10, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, -0.04, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, 0.02, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, 0.08, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, 0.12, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, 0.06, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, 0.00, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, -0.05, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, -0.10, 0.0],
                'duration': 250,
            },
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.40, 0.0, 0.0],
                'step_height': [0.04, 0.04],
                'body_height': 0.24,
                'rpy': [0.0, -0.02, 0.0],
                'duration': 250,
            },
            # 扭屁股（接口表：编号144 -> mode=62, gait_id=4）
            {'mode': 62, 'gait_id': 4, 'duration': 4000},
        ],
        # 姿态展示 / QP_STAND 收尾
        'stop_motion': {'mode': 3, 'gait_id': 0, 'body_height': 0.22, 'duration': 600},
    },

    'sad': {
        'type': 'single',
        'demo_seconds': 4.0,
        'sequence': [
            {'mode': 12, 'gait_id': 0, 'duration': 6000},
            # 绝对站高先下压
            {'mode': 21, 'gait_id': 5, 'body_height': 0.19, 'duration': 500},
            # 相对俯仰低头
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [0.0, -0.12, 0.0], 'duration': 500},
            # 慢走（接口表：编号303 -> mode=11, gait_id=27）
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.05, 0.0, 0.0],
                'step_height': [0.02, 0.02],
                'body_height': 0.19,
                'duration': 1200,
            },
            # 坐下（接口表：编号143 -> mode=62, gait_id=3，不是 mode=143）
            {'mode': 62, 'gait_id': 3, 'duration': 1800},
        ],
    },

    'fearful': {
        'type': 'single',
        'demo_seconds': 4.0,
        'sequence': [
            {'mode': 21, 'gait_id': 5, 'body_height': 0.20, 'duration': 400},
            {'mode': 21, 'gait_id': 0, 'position': [-0.02, 0.0, 0.0], 'rpy': [0.0, -0.08, 0.0], 'duration': 500},
            {
                'mode': 11,
                'gait_id': 27,
                'velocity': [-0.22, 0.0, 0.0],
                'step_height': [0.015, 0.015],
                'body_height': 0.20,
                'duration': 1100,
            },
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [0.02, -0.08, 0.05], 'duration': 220},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [-0.02, -0.08, -0.05], 'duration': 220},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [0.0, -0.08, 0.35], 'duration': 500},
        ],
    },

    'angry': {
        'type': 'single',
        'demo_seconds': 3.0,
        'sequence': [
            {'mode': 12, 'gait_id': 0, 'duration': 6000},
            {'mode': 21, 'gait_id': 5, 'body_height': 0.23, 'duration': 400},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [0.0, -0.12, 0.0], 'duration': 300},
            {
                'mode': 11,
                'gait_id': 10,
                'velocity': [0.80, 0.0, 0.0],
                'step_height': [0.05, 0.05],
                'body_height': 0.23,
                'duration': 900,
            },
            {'mode': 21, 'gait_id': 0, 'position': [0.02, 0.0, 0.0], 'rpy': [0.0, -0.14, 0.0], 'duration': 180},
            {'mode': 21, 'gait_id': 0, 'position': [0.02, 0.0, 0.0], 'rpy': [0.0, -0.14, 0.0], 'duration': 180},
            {'mode': 3, 'gait_id': 0, 'body_height': 0.23, 'duration': 800},
        ],
    },

    'disgusted': {
        'type': 'single',
        'demo_seconds': 3.0,
        'sequence': [
            {'mode': 21, 'gait_id': 5, 'body_height': 0.22, 'duration': 400},
            {'mode': 21, 'gait_id': 0, 'position': [-0.02, 0.0, 0.0], 'rpy': [0.0, 0.0, 0.0], 'duration': 300},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [0.0, 0.0, 0.50], 'duration': 450},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [0.04, 0.0, 0.28], 'duration': 220},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [-0.04, 0.0, 0.28], 'duration': 220},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [0.0, 0.0, 0.28], 'duration': 800},
        ],
    },

    'surprised': {
        'type': 'single',
        'demo_seconds': 2.0,
        'sequence': [
            {'mode': 21, 'gait_id': 5, 'body_height': 0.25, 'duration': 300},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [0.0, 0.10, 0.30], 'duration': 280},
            {'mode': 21, 'gait_id': 0, 'position': [0.0, 0.0, 0.0], 'rpy': [0.0, 0.10, 0.30], 'duration': 700},
            {'mode': 3, 'gait_id': 0, 'body_height': 0.22, 'duration': 500},
        ],
    },
}

EMOTION_CONFIGS = PDF_EMOTION_CONFIGS
