"""
motor_rr_test.py —— RR(右后) 电机闭环验证

接线:
    GPIO47 -> PWMC     GPIO3  -> CIN1    GPIO4  -> CIN2
    GPIO02 -> STBY     GPIO5  <- E3A     GPIO6  <- E3B

注意:
    GPIO3~6 复用 JTAG(TDI/TDO/TMS/RST) 与 UART1/UART2。
    不用 JTAG 调试、不用这两路串口即可。

用法:
    python k230_run.py motor_closed.py motor_test_lib.py motor_rr_test.py COM12
"""
from machine import FPIOA, Pin
import time

try:
    from motor_closed import ClosedMotor
    from motor_test_lib import verify
except ImportError:
    pass

# ================= 配置 =================
NAME = "RR"
PWM_ID = 3
PIN_PWM = 47
PIN_IN1 = 3
PIN_IN2 = 4
PIN_ENC_A = 5
PIN_ENC_B = 6
PIN_STBY = 2

if __name__ == "__main__":
    fpioa = FPIOA()
    fpioa.set_function(PIN_STBY, FPIOA.GPIO2)
    stby = Pin(PIN_STBY, Pin.OUT)

    motor = ClosedMotor(PWM_ID, PIN_PWM, PIN_IN1, PIN_IN2,
                        PIN_ENC_A, PIN_ENC_B, fpioa=fpioa, name=NAME)

    print("引脚: PWMC=%d  CIN1=%d  CIN2=%d  E3A=%d  E3B=%d"
          % (PIN_PWM, PIN_IN1, PIN_IN2, PIN_ENC_A, PIN_ENC_B))

    stby.value(1)
    time.sleep(0.2)
    verify(motor, NAME)
    time.sleep(0.3)
    stby.value(0)
    print("=== 完成 ===")
