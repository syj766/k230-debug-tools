"""
test_fr.py —— FR(右前) 单独前进测试

用法:
    python k230_run.py ../motor_closed.py test_fr.py COM12
"""
from machine import FPIOA, Pin
import time

try:
    from motor_closed import ClosedMotor
except ImportError:
    pass

NAME = "FR"
PWM_ID = 4
PIN_PWM = 52
PIN_IN1 = 32
PIN_IN2 = 33
PIN_ENC_A = 34
PIN_ENC_B = 35
PIN_STBY = 2

OTHER_IN = (14, 15, 36, 37, 3, 4)
OTHER_PWM = (61, 46, 47)

STEPS = (300, 500, 700, 0)
STEP_MS = 3000

if __name__ == "__main__":
    fpioa = FPIOA()

    fpioa.set_function(PIN_STBY, FPIOA.GPIO2)
    stby = Pin(PIN_STBY, Pin.OUT, value=0)

    for p in OTHER_IN + OTHER_PWM:
        fpioa.set_function(p, FPIOA.GPIO0)
        Pin(p, Pin.OUT, value=0)

    motor = ClosedMotor(PWM_ID, PIN_PWM, PIN_IN1, PIN_IN2,
                        PIN_ENC_A, PIN_ENC_B, fpioa=fpioa, name=NAME)

    print("=== %s 前进测试 ===" % NAME)
    print("引脚: PWM%d=%d  IN1=%d  IN2=%d  E_A=%d  E_B=%d  STBY=%d"
          % (PWM_ID, PIN_PWM, PIN_IN1, PIN_IN2, PIN_ENC_A, PIN_ENC_B, PIN_STBY))

    stby.value(1)
    time.sleep(0.2)

    try:
        if not motor.calibrate_sign():
            print("[失败] 编码器无信号")
        else:
            print("[标定] sign=%+d  count=%d" % (motor.sign, motor.last_calib_count))

            for target in STEPS:
                motor.set_target(target)
                print("--- 目标 %+d Hz ---" % target)
                t0 = time.ticks_ms()
                n = 0
                while time.ticks_diff(time.ticks_ms(), t0) < STEP_MS:
                    motor.update(20)
                    n += 1
                    if n % 12 == 0:
                        print("  t=%4dms  speed=%+5d  duty=%+4d"
                              % (time.ticks_diff(time.ticks_ms(), t0),
                                 int(motor.speed), motor.duty))
    finally:
        motor.stop()
        time.sleep(0.2)
        stby.value(0)
        print("=== %s 完成 ===" % NAME)