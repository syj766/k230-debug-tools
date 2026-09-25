"""
motor_test_lib.py —— 电机验证流程通用库

四个轮子(FL/RL/RR/FR)共用同一套验证流程, 各自只需在测试文件里给引脚配置。

流程:
    [1] 方向标定   —— 检查 E1A/E1B 接线与极性(极性反了自动修正)
    [2] 空载跟踪   —— +300 / +600 / -600 Hz 稳态精度
    [3] 抗负载     —— 手捏轮子, duty 是否自动上升而速度维持(闭环铁证)

用法:
    python k230_run.py motor_closed.py motor_test_lib.py motor_fl_test.py COM12
"""
import time

TARGETS = (300, 600, -600)      # 空载跟踪目标(Hz)
RUN_MS = 2000                   # 每档运行时长
LOAD_TARGET = 600               # 抗负载测试的目标速度
LOAD_MS = 2500                  # 抗负载测试时长


def _report(motor, t0):
    print("  t=%4dms  速度=%+5d Hz  duty=%+4d"
          % (time.ticks_diff(time.ticks_ms(), t0),
             int(motor.speed), motor.duty))


def _run(motor, target, ms):
    motor.set_target(target)
    print("--- 目标 %+d Hz ---" % target)
    t0 = time.ticks_ms()
    n = 0
    while time.ticks_diff(time.ticks_ms(), t0) < ms:
        motor.update(20)
        n += 1
        if n % 12 == 0:
            _report(motor, t0)


def verify(motor, name="", targets=TARGETS, run_ms=RUN_MS,
           load_target=LOAD_TARGET, load_ms=LOAD_MS):
    """标准验证流程。返回 True = 通过, False = 编码器无信号"""
    print("=== %s 电机闭环验证 ===" % (name or motor.name))

    if not motor.calibrate_sign():
        print("[失败] 编码器无信号: 标定计数=%d  E1A=%d  E1B=%d"
              % (motor.last_calib_count, motor.ea.value(), motor.eb.value()))
        return False

    print("[1] 方向标定 OK: sign=%+d  (标定计数=%d)"
          % (motor.sign, motor.last_calib_count))

    print("[2] 空载跟踪")
    for t in targets:
        _run(motor, t, run_ms)

    print("[3] 抗负载 —— duty 上升 + 速度维持 = 闭环生效")
    _run(motor, load_target, load_ms)

    motor.stop()
    return True
