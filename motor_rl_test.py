"""
motor_rl_test.py —— RL(左后) 电机闭环验证

接线:
    GPIO46 -> PWMB     GPIO36 -> BIN1    GPIO37 -> BIN2
    GPIO02 -> STBY     GPIO40 <- E2A     GPIO41 <- E2B

注意:
    GPIO40/41 是 I2C1(板载摄像头1), 不用摄像头时可用。
    该脚带板载 I2C 上拉, 对开漏输出的霍尔编码器反而有利(已实测通过)。
    若以后要用摄像头, 这两脚需另找位置。

用法:
    python k230_run.py motor_closed.py motor_test_lib.py motor_rl_test.py COM12
"""
from machine import FPIOA, Pin
import time

try:
    from motor_closed import ClosedMotor
    from motor_test_lib import verify
except ImportError:
    pass

# ================= 配置 =================
NAME = "RL"
PWM_ID = 2
PIN_PWM = 46
PIN_IN1 = 36
PIN_IN2 = 37
PIN_ENC_A = 40
PIN_ENC_B = 41
PIN_STBY = 2

if __name__ == "__main__":
    fpioa = FPIOA()
    fpioa.set_function(PIN_STBY, FPIOA.GPIO2)
    stby = Pin(PIN_STBY, Pin.OUT)

    motor = ClosedMotor(PWM_ID, PIN_PWM, PIN_IN1, PIN_IN2,
                        PIN_ENC_A, PIN_ENC_B, fpioa=fpioa, name=NAME)

    print("引脚: PWMB=%d  BIN1=%d  BIN2=%d  E2A=%d  E2B=%d"
          % (PIN_PWM, PIN_IN1, PIN_IN2, PIN_ENC_A, PIN_ENC_B))

    stby.value(1)
    time.sleep(0.2)
    verify(motor, NAME)
    time.sleep(0.3)
    stby.value(0)
    print("=== 完成 ===")
