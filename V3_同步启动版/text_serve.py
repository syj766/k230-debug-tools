"""
servo_test.py
K230 + SG90 舵机测试
GPIO42 -> 舵机信号线
舵机 VCC -> 5V
舵机 GND -> GND
K230 GND 与舵机电源 GND 共地
"""

from machine import FPIOA, PWM
import time

# =========================
# 1. GPIO42 复用为 PWM0
# =========================
fpioa = FPIOA()
fpioa.set_function(42, FPIOA.PWM0)

# =========================
# 2. 初始化 PWM
#    50Hz -> 周期20ms
# =========================
servo = PWM(0, freq=50, duty=0)

print("[OK] Servo PWM started")
print("[INFO] freq =", servo.freq())

# =========================
# 3. 0° 位置
#    0.5ms 高电平 = 500000ns
# =========================
print("[TEST] 0度")
servo.duty_ns(500000)
time.sleep(2)

# =========================
# 4. 90° 位置
#    1.5ms 高电平 = 1500000ns
# =========================
print("[TEST] 90度")
servo.duty_ns(1500000)
time.sleep(2)

# =========================
# 5. 回 0°
# =========================
print("[TEST] 回0度")
servo.duty_ns(500000)
time.sleep(2)

# =========================
# 6. 停止输出
# =========================
servo.duty_ns(0)
servo.deinit()

print("[DONE] 测试结束")