"""
CyberDog2 LCM 通信控制
基于 loco_hl_example/basic_motion/main.py
"""

import lcm
import time
import threading
from robot_control_cmd_lcmt import robot_control_cmd_lcmt
from robot_control_response_lcmt import robot_control_response_lcmt


class CyberDogController:
    """CyberDog2 LCM 通信控制器"""

    TX_URL = "udpm://239.255.76.67:7671?ttl=255"
    RX_URL = "udpm://239.255.76.67:7670?ttl=255"
    CHAN_CMD = "robot_control_cmd"
    CHAN_RESP = "robot_control_response"
    HEARTBEAT_INTERVAL = 0.02

    def __init__(self):
        self.lcm_tx = lcm.LCM(self.TX_URL)
        self.lcm_rx = lcm.LCM(self.RX_URL)
        self.subscription = self.lcm_rx.subscribe(self.CHAN_RESP, self._on_response)
        self.response = None
        self.life_count = 1
        self.running = True
        self._latest_cmd = None
        self._tx_lock = threading.Lock()

        # 启动接收线程
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self.tx_thread = threading.Thread(target=self._tx_loop, daemon=True)
        self.rx_thread.start()
        self.tx_thread.start()

    def _rx_loop(self):
        """接收响应线程"""
        while self.running:
            self.lcm_rx.handle_timeout(50)

    def _tx_loop(self):
        """周期性重发最近命令，维持 heartbeat。"""
        while self.running:
            with self._tx_lock:
                latest_cmd = self._latest_cmd
            if latest_cmd is not None:
                self.lcm_tx.publish(self.CHAN_CMD, latest_cmd.encode())
            time.sleep(self.HEARTBEAT_INTERVAL)

    def _on_response(self, channel, data):
        """LCM 响应回调"""
        try:
            self.response = robot_control_response_lcmt.decode(data)
        except Exception as e:
            print(f"Response decode error: {e}")

    def _next_life_count(self):
        if self.life_count < 1 or self.life_count >= 127:
            self.life_count = 1
        current = self.life_count
        self.life_count += 1
        if self.life_count >= 127:
            self.life_count = 1
        return current

    def send_command(self, mode, gait_id=0, velocity=[0, 0, 0],
                     step_height=[0, 0], body_height=0.20,
                     position=[0, 0, 0], rpy=[0, 0, 0],
                     duration=0):
        """
        发送运动命令到 CyberDog2

        Args:
            mode: Motion mode or action identifier used by the active emotion configuration.
            gait_id: Gait identifier used by the active emotion configuration.
            velocity: [vx, vy, yaw_rate] target locomotion velocity.
            step_height: [front, back] leg lift height.
            body_height: Body height used when no explicit position is provided.
            position: [x, y, z] position target for pose control motions.
            rpy: [roll, pitch, yaw] orientation target.
            duration: Motion duration in milliseconds; 0 means continue until superseded.
        """
        msg = robot_control_cmd_lcmt()
        msg.mode = mode
        msg.gait_id = gait_id
        msg.life_count = self._next_life_count()
        msg.contact = 0x0F  # 所有腿接触
        msg.vel_des = velocity
        msg.step_height = step_height
        if mode == 21 and gait_id == 0:
            msg.pos_des = position
        elif mode == 21 and gait_id == 5:
            msg.pos_des = [0, 0, body_height]
        else:
            msg.pos_des = [0, 0, body_height]
        msg.rpy_des = rpy
        msg.duration = duration

        with self._tx_lock:
            self._latest_cmd = msg
        self.lcm_tx.publish(self.CHAN_CMD, msg.encode())
        return msg

    def wait_finish(self, mode=None, gait_id=None, timeout=10.0):
        """等待动作完成"""
        start = time.time()
        while (time.time() - start) < timeout:
            response = self.response
            if response and response.order_process_bar >= 95:
                mode_matches = mode is None or response.mode == mode
                gait_matches = gait_id is None or response.gait_id == gait_id
                if mode_matches and gait_matches:
                    return True
            time.sleep(0.1)
        return False

    def get_response(self):
        """获取最新响应"""
        return self.response

    def close(self):
        """关闭连接"""
        self.running = False
        self.lcm_rx.unsubscribe(self.subscription)
        self.rx_thread.join(timeout=0.1)
        self.tx_thread.join(timeout=0.1)


def create_stand_cmd(body_height=0.20, rpy=[0, 0, 0]):
    """创建站立命令"""
    return {
        'mode': 3,
        'gait_id': 0,
        'body_height': body_height,
        'rpy': rpy,
        'duration': 0,
    }


def create_trot_cmd(velocity=[0.3, 0, 0], step_height=[0.06, 0.06], body_height=0.18, duration=0):
    """创建小跑命令"""
    return {
        'mode': 11,
        'gait_id': 3,  # trot_medium
        'velocity': velocity,
        'step_height': step_height,
        'body_height': body_height,
        'duration': duration,
    }


def create_lie_down_cmd(duration=3500):
    """创建趴下命令"""
    return {
        'mode': 7,
        'gait_id': 1,
        'duration': duration,
    }


def create_jump_cmd(duration=1200):
    """创建跳跃命令"""
    return {
        'mode': 16,
        'gait_id': 6,  # jump_up
        'duration': duration,
    }