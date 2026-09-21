"""
motor_fl_test.py —— FL(左前) 电机闭环验证

接线:
    GPIO61 -> PWMA     GPIO14 -> AIN1    GPIO15 -> AIN2
    GPIO02 -> STBY     GPIO17 <- E1A     GPIO27 <- E1B

用法(拼接执行, 板上无需存库文件):
    python k230_run.py motor_closed.py motor_test_lib.py motor_fl_test.py COM12
"""
from machine import FPIOA, Pin
import time

# 拼接执行时前面的文件已经定义了这些符号; 若单独 import 本文件则需要库
try:
    from motor_closed import ClosedMotor
    from motor_test_lib import verify
except ImportError:
    pass

# ================= 配置 =================
NAME = "FL"
PWM_ID = 1
PIN_PWM = 61
PIN_IN1 = 14
PIN_IN2 = 15
PIN_ENC_A = 17
PIN_ENC_B = 27
PIN_STBY = 2

if __name__ == "__main__":
    fpioa = FPIOA()
    fpioa.set_function(PIN_STBY, FPIOA.GPIO2)
    stby = Pin(PIN_STBY, Pin.OUT)

    motor = ClosedMotor(PWM_ID, PIN_PWM, PIN_IN1, PIN_IN2,
                        PIN_ENC_A, PIN_ENC_B, fpioa=fpioa, name=NAME)

    print("引脚: PWMA=%d  AIN1=%d  AIN2=%d  E1A=%d  E1B=%d"
          % (PIN_PWM, PIN_IN1, PIN_IN2, PIN_ENC_A, PIN_ENC_B))

    stby.value(1)
    time.sleep(0.2)
    verify(motor, NAME)
    time.sleep(0.3)
    stby.value(0)
    print("=== 完成 ===")
