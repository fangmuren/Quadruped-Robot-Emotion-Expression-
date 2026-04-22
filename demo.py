"""
六情绪动作演示脚本
按顺序演示每种情绪的动作
"""

import time
from emotion import SixEmotions, get_emotion_config, get_post_execute_wait_seconds
from robot_control import CyberDogController
from motion_sequence import MotionSequence


def demo_all_emotions():
    """演示所有六种情绪动作"""
    print("=" * 60)
    print("CyberDog2 六情绪动作演示")
    print("=" * 60)

    controller = CyberDogController()
    sequencer = MotionSequence(controller)

    try:
        for emotion in SixEmotions.ALL:
            config = get_emotion_config(emotion)
            print(f"\n{'='*60}")
            print(f">>> 执行情绪: {emotion} (类型: {config['type']})")
            print(f"{'='*60}")

            sequencer.execute_emotion(emotion)
            wait_seconds = get_post_execute_wait_seconds(emotion)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            if config['type'] == 'loop':
                sequencer.stop()
                time.sleep(0.5)

            print(f">>> {emotion} 执行完成\n")

    except KeyboardInterrupt:
        print("\n演示被中断")
        sequencer.stop()
    finally:
        controller.close()
        print("演示结束")


if __name__ == "__main__":
    demo_all_emotions()