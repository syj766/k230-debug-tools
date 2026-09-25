"""
motor_manager.py —— 多电机共享采样层 + 底盘（第二层 / 第三层）

分层职责:
    poll_all()      第二层核心: 一个时间窗口内同时采样所有电机编码器
    MotorManager    管理一组电机: 统一采样 -> 逐个控制
    Chassis         第三层: 左右差速, 上层只给 left/right 速度

为什么必须共享采样:
    若 4 轮各自 update(20), 总周期 = 4 x 20 = 80ms, 太慢。
    共享窗口后总周期仍为 20ms, 采样率降到约 1/4 —— 相对 2kHz 的编码器
    信号依然充裕(实测单路 69kHz, 四路约 15~20kHz)。

用法(四驱):
    motors = [ClosedMotor(...) for i in range(4)]
    chassis = Chassis(motors[0:2], motors[2:4])   # 左两轮 / 右两轮
    chassis.set_velocity(600, 600)                # 直行
    while True:
        chassis.update()
"""
import time

# 单独 import 本模块时从 motor_closed 取; 拼接执行时符号已在前面的代码里
try:
    from motor_closed import ClosedMotor, PIController, _QUAD
except ImportError:
    pass


def poll_all(motors, ms):
    """共享一个 ms 毫秒窗口, 同时采样多个电机。

    返回 (counts, dt_ms):
        counts —— 各电机的原始计数(未乘方向符号)
        dt_ms  —— 实际窗口长度, 用于速度换算(比名义值更准)
    """
    n = len(motors)
    counts = [0] * n
    states = [m.read_state() for m in motors]

    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < ms:
        for i in range(n):
            m = motors[i]
            ns = m.read_state()
            if ns != states[i]:
                counts[i] += _QUAD[(states[i] << 2) | ns]
                states[i] = ns

    return counts, time.ticks_diff(time.ticks_ms(), t0)


class MotorManager:
    """一组电机的统一采样 + 更新"""

    def __init__(self, motors, sample_ms=20):
        self.motors = list(motors)
        self.sample_ms = sample_ms

    def update(self):
        """一个共享控制周期: 采样一次 -> 各电机各自控制"""
        counts, dt = poll_all(self.motors, self.sample_ms)
        for m, c in zip(self.motors, counts):
            m.apply_count(c, dt)
        return dt

    def set_target(self, *targets):
        for m, t in zip(self.motors, targets):
            m.set_target(t)

    def speeds(self):
        return [m.speed for m in self.motors]

    def calibrate(self):
        """逐个标定方向, 返回标定失败的电机名列表"""
        bad = []
        for m in self.motors:
            if not m.calibrate_sign():
                bad.append(m.name)
        return bad

    def stop(self):
        for m in self.motors:
            m.stop()


class Chassis:
    """左右差速底盘: 硬件四路独立闭环, 软件左右联动"""

    def __init__(self, left, right, sample_ms=20):
        self.left = list(left)
        self.right = list(right)
        self.motors = self.left + self.right
        self.manager = MotorManager(self.motors, sample_ms)

    def set_velocity(self, left_hz, right_hz):
        """设定左右速度(Hz, 带符号); 每个轮子闭环独立"""
        for m in self.left:
            m.set_target(left_hz)
        for m in self.right:
            m.set_target(right_hz)

    def turn(self, base_hz, diff_hz):
        """差速转向: 左 = base-diff, 右 = base+diff"""
        self.set_velocity(base_hz - diff_hz, base_hz + diff_hz)

    def update(self):
        return self.manager.update()

    def speeds(self):
        return self.manager.speeds()

    def stop(self):
        self.manager.stop()
