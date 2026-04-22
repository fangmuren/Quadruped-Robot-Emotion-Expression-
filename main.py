"""
CyberDog2 六情绪动作 - 主程序入口
"""

import argparse
import time
from emotion import SixEmotions, get_post_execute_wait_seconds, get_runtime_policy
from robot_control import CyberDogController
from motion_sequence import MotionSequence


def main():
    parser = argparse.ArgumentParser(
        description='CyberDog2 六情绪动作控制系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
可用情绪:
  happy     - 开心
  sad       - 委屈
  fearful   - 惊恐
  angry     - 愤怒
  disgusted - 厌恶
  surprised - 惊讶

示例:
  python main.py happy      # 执行开心动作
  python main.py sad        # 执行委屈动作
  python main.py --list     # 列出所有情绪
        """
    )
    parser.add_argument('emotion', nargs='?', choices=SixEmotions.ALL, help='情绪类型')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有可用情绪')
    parser.add_argument('--loop', action='store_true', help='循环执行直到 Ctrl+C')

    args = parser.parse_args()

    if args.list:
        print("可用情绪:")
        for e in SixEmotions.ALL:
            print(f"  - {e}")
        return

    if not args.emotion:
        parser.print_help()
        return

    controller = CyberDogController()
    sequencer = MotionSequence(controller)

    print(f"执行情绪: {args.emotion}")

    try:
        sequencer.execute_emotion(args.emotion)

        runtime_type, _demo_seconds = get_runtime_policy(args.emotion)
        wait_seconds = get_post_execute_wait_seconds(args.emotion)

        if args.loop and runtime_type == 'loop':
            print("循环模式，按 Ctrl+C 停止")
            while sequencer.is_running():
                time.sleep(0.1)
        elif runtime_type == 'loop' and wait_seconds > 0:
            print(f"演示 {wait_seconds:.1f} 秒后停止...")
            time.sleep(wait_seconds)
            sequencer.stop()

    except KeyboardInterrupt:
        print("\n被中断，停止动作")
        sequencer.stop()
    finally:
        controller.close()
        print("程序结束")


if __name__ == "__main__":
    main()