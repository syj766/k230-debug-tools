"""
motor.py - 双电机测试
K230 + TB6612FNG 控制两个 MG513 电机
"""

from machine import FPIOA, PWM, Pin
import time

# ========== 引脚配置 ==========
fpioa = FPIOA()

# --- 电机A ---
fpioa.set_function(61, FPIOA.PWM1)   # GPIO61 → PWMA
fpioa.set_function(40, FPIOA.GPIO40)  # GPIO40 → AIN1
fpioa.set_function(41, FPIOA.GPIO41)  # GPIO41 → AIN2

# --- 电机B ---
fpioa.set_function(46, FPIOA.PWM2)   # GPIO46 → PWMB
fpioa.set_function(15, FPIOA.GPIO15)  # GPIO15 → BIN1
fpioa.set_function(16, FPIOA.GPIO16)  # GPIO16 → BIN2

# STBY 共用
fpioa.set_function(2, FPIOA.GPIO2)  # GPIO2 → STBY

# ========== 初始化 ==========
pwm_a = PWM(1, freq=10000, duty=0)
ain1 = Pin(40, Pin.OUT)
ain2 = Pin(41, Pin.OUT)

pwm_b = PWM(2, freq=10000, duty=0)
bin1 = Pin(15, Pin.OUT)
bin2 = Pin(16, Pin.OUT)

stby = Pin(2, Pin.OUT)

#初始化封装
def motor_init():
    stby.value(1)
    print("[OK] 双电机驱动已使能")

#反初始化,停止两个电机,关闭STBY,注销PWM资源
def motor_deinit():
    motor_a.set_speed(0)
    motor_b.set_speed(0)
    stby.value(0)
    pwm_a.deinit()
    pwm_b.deinit()
    print("[X] 双电机驱动已关闭")

# ========== 电机类 ==========
#Motor命名随意，哪个好听取哪个
class Motor:
    def __init__(self, pwm, pin1, pin2, name="Motor"):
        self.pwm = pwm
        self.pin1 = pin1
        self.pin2 = pin2
        self.name = name
        self.target_speed = 0

    def set_speed(self, speed):
        speed = int(speed)
        speed = max(-100, min(100, speed))
        self.target_speed = speed

        if speed > 0:
            self.pin1.value(1)
            self.pin2.value(0)
            self.pwm.duty(speed)
            # print(f"[{self.name}→] 正转, 占空比: {speed}%")
        elif speed < 0:
            self.pin1.value(0)
            self.pin2.value(1)
            self.pwm.duty(-speed)
            # print(f"[{self.name}←] 反转, 占空比: {-speed}%")
        else:
            self.pin1.value(0)
            self.pin2.value(0)
            self.pwm.duty(0)
            # print(f"[{self.name}○] 停止")

    def brake(self):
        self.target_speed = 0
        self.pin1.value(1)
        self.pin2.value(1)
        self.pwm.duty(0)
        # print(f"[{self.name}■] 刹车")

#一次定义，多次使用
motor_a = Motor(pwm_a, ain1, ain2, "A") #from motor import motor_a, motor_b(car.py)
motor_b = Motor(pwm_b, bin1, bin2, "B")

# ========== 测试程序 ==========

if __name__ == "__main__":
    try:
        motor_init()

        
        print("\n=== 双电机测试开始 ===")
        
        print("\n[测试1] 双电机低速正转...")
        motor_a.set_speed(30)
        motor_b.set_speed(30)
        time.sleep(2)
        
        print("\n[测试2] 双电机中速正转...")
        motor_a.set_speed(60)
        motor_b.set_speed(60)
        time.sleep(2)
        
        print("\n[测试3] 双电机停止...")
        motor_a.set_speed(0)
        motor_b.set_speed(0)
        time.sleep(1)
        
        print("\n[测试4] 原地旋转（A正B反）...")
        motor_a.set_speed(40)
        motor_b.set_speed(-40)
        time.sleep(2)
        
        print("\n[测试5] 双电机刹车...")
        motor_a.brake()
        motor_b.brake()
        time.sleep(1)
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"[错误] {e}")
    finally:
        motor_deinit()