"""
test_forward.py —— 四轮同步前进测试

接线: 与 test_chassis.py 一致
    FL  61 / 14,15 / 17,27      RL  46 / 36,37 / 40,41
    RR  47 / 3,4   / 5,6        FR  52 / 32,33 / 34,35
    STBY = GPIO2 (共用)

用法:
    python k230_run.py motor_closed.py motor_manager.py test_forward.py COM12

说明:
    四轮各自闭环独立, 用 MotorManager 统一 20ms 采样窗口。
    先初始化全部引脚再拉 STBY, 避免未配置脚导致其他轮误转。
"""
from machine import FPIOA, Pin
import time

try:
    from motor_closed import ClosedMotor
    from motor_manager import MotorManager
except ImportError:
    pass

MOTORS = (
    ("FL", 1, 61, 14, 15, 17, 27, False),
    ("RL", 2, 46, 36, 37, 40, 41, True),
    ("RR", 3, 47,  3,  4,  5,  6, True),
    ("FR", 4, 52, 32, 33, 34, 35, False),
)
PIN_STBY = 2

STEPS = (
    (300,   "低速前进"),
    (500,   "中速前进"),
    (700,   "高速前进"),
    (0,     "停止"),
)
STEP_MS = 3000


def show(mgr, t0):
    sp = mgr.speeds()
    print("  t=%4dms  FL=%+5d  RL=%+5d  RR=%+5d  FR=%+5d  duty=%s"
          % (time.ticks_diff(time.ticks_ms(), t0),
             int(sp[0]), int(sp[1]), int(sp[2]), int(sp[3]),
             [m.duty for m in mgr.motors]))


if __name__ == "__main__":
    fpioa = FPIOA()
    fpioa.set_function(PIN_STBY, FPIOA.GPIO2)
    stby = Pin(PIN_STBY, Pin.OUT, value=0)

    motors = []
    for name, pwm_id, pwm, in1, in2, ea, eb, invert in MOTORS:
        motors.append(ClosedMotor(pwm_id, pwm, in1, in2, ea, eb,
                                  fpioa=fpioa, name=name, invert_dir=invert))

    mgr = MotorManager(motors, sample_ms=20)

    print("=== 四轮前进测试 ===")
    print("引脚: FL=PWM1/61  RL=PWM2/46  RR=PWM3/47  FR=PWM4/52")
    print("STBY=GPIO2")

    stby.value(1)
    time.sleep(0.2)

    try:
        bad = mgr.calibrate()
        if bad:
            print("[失败] 编码器无信号:", bad)
            print("       先单独跑对应的 motor_xx_test.py 排查接线")
        else:
            print("[1] 标定 OK  (sign: %s)"
                  % ", ".join("%s=%+d" % (m.name, m.sign) for m in motors))

            for target, tag in STEPS:
                print("--- %s: %+d Hz ---" % (tag, target))
                mgr.set_target(*([target] * 4))
                t0 = time.ticks_ms()
                n = 0
                while time.ticks_diff(time.ticks_ms(), t0) < STEP_MS:
                    mgr.update()
                    n += 1
                    if n % 15 == 0:
                        show(mgr, t0)

    finally:
        mgr.stop()
        time.sleep(0.3)
        stby.value(0)
        print("=== 完成 ===")