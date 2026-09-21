"""
motor_fr_test.py —— FR(右前) 电机闭环验证

接线:
    GPIO52 -> PWMD     GPIO32 -> DIN1    GPIO33 -> DIN2
    GPIO02 -> STBY     GPIO34 <- E4A     GPIO35 <- E4B

注意:
    GPIO32/33 复用 UART3(板载 GH1.25 调试座并联引出), 别同时插调试器。
    GPIO34/35 复用 IIS / PDM / IIC1, 不用音频与摄像头1即可。

用法:
    python k230_run.py motor_closed.py motor_test_lib.py motor_fr_test.py COM12
"""
from machine import FPIOA, Pin
import time

try:
    from motor_closed import ClosedMotor
    from motor_test_lib import verify
except ImportError:
    pass

# ================= 配置 =================
NAME = "FR"
PWM_ID = 4
PIN_PWM = 52
PIN_IN1 = 32
PIN_IN2 = 33
PIN_ENC_A = 34
PIN_ENC_B = 35
PIN_STBY = 2

if __name__ == "__main__":
    fpioa = FPIOA()
    fpioa.set_function(PIN_STBY, FPIOA.GPIO2)
    stby = Pin(PIN_STBY, Pin.OUT)

    motor = ClosedMotor(PWM_ID, PIN_PWM, PIN_IN1, PIN_IN2,
                        PIN_ENC_A, PIN_ENC_B, fpioa=fpioa, name=NAME)

    print("引脚: PWMD=%d  DIN1=%d  DIN2=%d  E4A=%d  E4B=%d"
          % (PIN_PWM, PIN_IN1, PIN_IN2, PIN_ENC_A, PIN_ENC_B))

    stby.value(1)
    time.sleep(0.2)
    verify(motor, NAME)
    time.sleep(0.3)
    stby.value(0)
    print("=== 完成 ===")
