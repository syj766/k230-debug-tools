"""
test_chassis.py —— 四驱底盘差速验证

前提: 四个电机都已单独验证通过(FL / RL / RR / FR)。

接线:
    FL  61 / 14,15 / 17,27      RL  46 / 36,37 / 40,41
    RR  47 / 3,4   / 5,6        FR  52 / 32,33 / 34,35
    STBY = GPIO2 (四个 TB6612 共用)

用法:
    python k230_run.py motor_closed.py motor_manager.py test_chassis.py COM12

说明:
    四个电机共享一个 20ms 采样窗口(见 poll_all), 控制周期仍是 20ms,
    不是 4 x 20ms。每个轮子的 PI 各自独立。
"""
from machine import FPIOA, Pin
import time

try:
    from motor_closed import ClosedMotor
    from motor_manager import Chassis
except ImportError:
    pass        # 拼接执行时符号已定义

# ---- (名称, PWM通道, PWM脚, IN1, IN2, E_A, E_B) ----
MOTORS = (
    ("FL", 1, 61, 14, 15, 17, 27),
    ("RL", 2, 46, 36, 37, 40, 41),
    ("RR", 3, 47,  3,  4,  5,  6),
    ("FR", 4, 52, 32, 33, 34, 35),
)
PIN_STBY = 2

# ---- (左速度, 右速度, 说明) ----
STEPS = (
    (400,  400, "直行"),
    (400,  200, "右转(左快右慢)"),
    (200,  400, "左转"),
    (400, -400, "原地右转(左右反向)"),
    (  0,    0, "停止"),
)
STEP_MS = 2000


def show(chassis, t0):
    sp = chassis.speeds()
    print("  t=%4dms  FL=%+5d  RL=%+5d  RR=%+5d  FR=%+5d"
          % (time.ticks_diff(time.ticks_ms(), t0),
             int(sp[0]), int(sp[1]), int(sp[2]), int(sp[3])))


if __name__ == "__main__":
    fpioa = FPIOA()
    fpioa.set_function(PIN_STBY, FPIOA.GPIO2)
    stby = Pin(PIN_STBY, Pin.OUT)

    motors = []
    for name, pwm_id, pwm, in1, in2, ea, eb in MOTORS:
        motors.append(ClosedMotor(pwm_id, pwm, in1, in2, ea, eb,
                                  fpioa=fpioa, name=name))
    fl, rl, rr, fr = motors

    # 左 = FL + RL, 右 = RR + FR
    chassis = Chassis([fl, rl], [rr, fr], sample_ms=20)

    print("=== 四驱底盘差速验证 ===")

    stby.value(1)
    time.sleep(0.2)

    bad = chassis.manager.calibrate()
    if bad:
        print("[失败] 以下电机编码器无信号:", bad)
        print("       先单独跑对应的 motor_xx_test.py 排查接线")
    else:
        print("[1] 四个电机方向标定 OK  (sign: %s)"
              % ", ".join("%s=%+d" % (m.name, m.sign) for m in motors))

        print("[2] 差速动作")
        for left, right, tag in STEPS:
            print("--- %s: 左=%+d 右=%+d Hz ---" % (tag, left, right))
            chassis.set_velocity(left, right)
            t0 = time.ticks_ms()
            n = 0
            while time.ticks_diff(time.ticks_ms(), t0) < STEP_MS:
                chassis.update()
                n += 1
                if n % 12 == 0:
                    show(chassis, t0)

        chassis.stop()

    time.sleep(0.3)
    stby.value(0)
    print("=== 完成 ===")
