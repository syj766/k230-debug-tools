"""
motor_closed.py —— K230 单电机闭环单元（第一层：单轮执行器）

接线（默认对应 A 电机）:
    GPIO61 -> PWMA     GPIO14 -> AIN1    GPIO15 -> AIN2
    GPIO02 -> STBY     GPIO17 <- E1A     GPIO27 <- E1B

本环境实测约束（决定了实现方式）:
    1. Pin.irq 持续中断会崩板        -> 只能用主循环轮询
    2. 固件无编码器/脉冲计数 API     -> 无硬件解码可用

分层:
    第一层 ClosedMotor   —— 单轮: 正交解码 + 前馈 PI + PWM 输出
    第二层 poll_all      —— 多轮共享一个采样窗口（motor_manager.py）
    第三层 Chassis       —— 左右差速（motor_manager.py）

update() 与 apply_count() 的分工:
    update(ms)      单机自测用: 自己采样一个窗口再控制（会阻塞 ms 毫秒）
    apply_count()   四驱用: 采样由 poll_all 统一完成, 本方法只做控制计算
"""
from machine import FPIOA, PWM, Pin
import time

# 正交解码表: 索引 = (旧状态 << 2) | 新状态, 状态 = (A << 1) | B
# 值 +1 / -1 / 0（非法跳变视为抖动, 记 0）
_QUAD = (0, 1, -1, 0,
         -1, 0, 0, 1,
         1, 0, 0, -1,
         0, -1, 1, 0)


class PIController:
    """位置式 PI 控制器（与外环前馈配合, 故不含 D 项）"""

    def __init__(self, kp, ki, integral_limit=200, output_limit=20):
        self.kp = kp
        self.ki = ki
        self.integral_limit = integral_limit
        self.output_limit = output_limit
        self.integral = 0

    def reset(self):
        self.integral = 0

    def update(self, error):
        self.integral += error
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
        out = self.kp * error + self.ki * self.integral
        return max(-self.output_limit, min(self.output_limit, out))


class ClosedMotor:
    """单电机速度闭环执行器（支持正转 / 反转）"""

    def __init__(self, pwm_id, pin_pwm, pin_in1, pin_in2,
                 pin_enc_a, pin_enc_b, fpioa=None, name="M",
                 ff=0.05, kp=0.10, ki=0.02, alpha=0.4,
                 integral_limit=200, ctrl_limit=20,
                 out_limit=60, pwm_freq=10000, invert_dir=False,
                 sign=None):
        self.name = name
        self.ff = ff                # 前馈系数: 每 Hz 约需多少 % 占空比
        self.alpha = alpha          # 速度低通滤波系数
        self.out_limit = out_limit  # 总输出限幅(%)

        if invert_dir:
            pin_in1, pin_in2 = pin_in2, pin_in1

        self.fpioa = fpioa if fpioa is not None else FPIOA()
        self.fpioa.set_function(pin_pwm, getattr(FPIOA, "PWM%d" % pwm_id))
        for p in (pin_in1, pin_in2, pin_enc_a, pin_enc_b):
            self.fpioa.set_function(p, getattr(FPIOA, "GPIO%d" % p))

        self.pwm = PWM(pwm_id, freq=pwm_freq, duty=0)
        self.in1 = Pin(pin_in1, Pin.OUT)
        self.in2 = Pin(pin_in2, Pin.OUT)
        self.ea = Pin(pin_enc_a, Pin.IN, Pin.PULL_UP)
        self.eb = Pin(pin_enc_b, Pin.IN, Pin.PULL_UP)

        self.pi = PIController(kp, ki, integral_limit, ctrl_limit)
        self.sign = sign if sign is not None else 1   # 标定后或预设确定
        self.speed = 0.0        # 滤波后的速度(Hz, 带符号)
        self.duty = 0           # 当前占空比
        self.target = 0         # 目标速度(Hz, 带符号)
        self.last_calib_count = 0

    # ================= 输出 =================
    def drive(self, duty):
        """duty >0 正转, <0 反转, 0 停止"""
        duty = max(-100, min(100, int(duty)))
        self.duty = duty
        if duty > 0:
            self.in1.value(1)
            self.in2.value(0)
            self.pwm.duty(duty)
        elif duty < 0:
            self.in1.value(0)
            self.in2.value(1)
            self.pwm.duty(-duty)
        else:
            self.in1.value(0)
            self.in2.value(0)
            self.pwm.duty(0)

    def brake(self):
        """刹车（电机两端短接）"""
        self.target = 0
        self.in1.value(1)
        self.in2.value(1)
        self.pwm.duty(0)

    # ================= 采样 =================
    def read_state(self):
        """当前正交状态 (A<<1)|B —— 供 poll_all 共享采样使用"""
        return (self.ea.value() << 1) | self.eb.value()

    def poll(self, ms):
        """单机采样: 轮询 ms 毫秒, 返回原始计数(未乘方向符号)"""
        count = 0
        state = self.read_state()
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < ms:
            ns = self.read_state()
            if ns != state:
                count += _QUAD[(state << 2) | ns]
                state = ns
        return count

    # ================= 方向标定 =================
    def calibrate_sign(self):
        """正转一下, 用计数符号确定方向。返回 False = 编码器无信号"""
        self.sign = 1
        self.drive(30)
        time.sleep(0.5)
        raw = self.poll(300)
        self.drive(0)
        time.sleep(0.3)
        self.last_calib_count = raw
        if raw == 0:
            return False
        self.sign = 1 if raw > 0 else -1
        return True

    # ================= 控制 =================
    def set_target(self, hz):
        """目标速度(Hz), 正=正转, 负=反转"""
        if self.target * hz < 0:        # 换向保护: 先停一下再反向
            self.drive(0)
            time.sleep(0.3)
        self.target = hz
        self.pi.reset()

    def apply_count(self, count, dt_ms):
        """用外部采样结果执行一次控制, 返回本次实测速度(Hz)

        四驱时由 poll_all 统一采样, 再逐个调用本方法, 避免各轮各自阻塞。
        """
        hz_raw = count * self.sign * 1000.0 / dt_ms / 4.0
        self.speed += self.alpha * (hz_raw - self.speed)
        out = self.ff * self.target + self.pi.update(self.target - self.speed)
        out = max(-self.out_limit, min(self.out_limit, out))
        self.drive(out)
        return hz_raw

    def update(self, ms=20):
        """单机自测: 自己采样一个窗口再控制（会阻塞 ms 毫秒）"""
        return self.apply_count(self.poll(ms), ms)

    def stop(self):
        self.target = 0
        self.speed = 0.0
        self.drive(0)
        self.pi.reset()


# 本文件只提供 ClosedMotor / PIController 两个类。
# 单机验证脚本已独立为 motor_fl_test.py:
#     python k230_run.py motor_closed.py motor_fl_test.py COM12