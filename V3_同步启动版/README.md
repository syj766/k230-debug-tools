# V3 — 同步启动版(去掉逐轮标定)

本目录是**第三版**。核心变化:**去掉每次启动时的逐个标定,四轮同步启动**。
前两版(根目录 V1、`V2_反向标定版/`)原样保留。

## 这一版做了什么

| 改前 | 改后 |
|------|------|
| 启动 → FL转 → RL转 → RR转 → FR转 → 开始测试 | 启动 → **四轮同步**开始测试 |
| 每次标定浪费 ~4 秒 | **零等待** |
| 标定失败还要排查 | 直接跑 |

## 具体改动

### 1. `motor_closed.py` — `ClosedMotor` 加 `sign` 参数

```python
# 改前
def __init__(self, ..., invert_dir=False):
    self.sign = 1      # 默认值, 靠 calibrate_sign() 覆盖

# 改后
def __init__(self, ..., invert_dir=False, sign=None):
    self.sign = sign if sign is not None else 1
```

**为什么**：以前 `sign` 只能通过 `calibrate_sign()` 动态测得(让轮子转一圈、读编码器方向)。现在允许构造时**直接传入已知值**,跳过动态标定。`calibrate_sign()` 逻辑保留作备用。

### 2. `test_chassis.py` — 硬编码 sign + 删标定块

```python
# 改前
MOTORS = (
    ("FL", 1, 61, 14, 15, 17, 27, False),        # 无 sign
    ...
)
# 改后
MOTORS = (
    ("FL", 1, 61, 14, 15, 17, 27, False, -1),    # sign=-1
    ("RL", 2, 46, 36, 37, 40, 41, True,  -1),
    ("RR", 3, 47,  3,  4,  5,  6, True,  +1),
    ("FR", 4, 52, 32, 33, 34, 35, False, +1),
)
```

删掉了整段逐轮标定(原先的 `bad = chassis.manager.calibrate()` 等)。

**为什么**：日志已确认 `sign` 值稳定,每次重复标定纯属浪费时间。删掉后**上电直接跑差速动作**。

### 3. `test_forward.py` — 同上

改动完全一样：`MOTORS` 加 `sign`、删 `calibrate()` 块,四轮同步前进。

## 本目录文件

- `motor_closed.py` — 单轮闭环(含 `sign` 参数)
- `motor_manager.py` — 多电机管理 / `Chassis` 差速底盘
- `test_forward.py` — 四轮同步前进测试
- `test_chassis.py` — 四驱差速测试
- `text_serve.py` — SG90 舵机测试(GPIO42,独立小工具)

## `test_chassis.py` 兼作"健康检查"

`test_chassis.py` 是一个 PID 闭环、目标速度恒定的稳态场景,非常适合当**在线自检**用:

- **四轮全非零** → 四路(编码器 / 驱动 / PWM / 电源)都通了,线路正常。
- **速度全 0** → 大概率没上电,优先查电源。

因为它是**稳态闭环**(`set_velocity(+400)` 期望恒速 +400),0 只有"异常"这一种含义,信号干净、判据明确。

> 对比 `test_forward.py`:它带着惯性/滑行的动态过程,速度会经历 0→加速→滑行→0,0 同时可能是"起点/终点"也可能是"没上电",语义有歧义,**不适合当健康判据**。

## 与根目录 / V2 的关系

- **V1(根目录)**:无 `invert_dir`、无 `sign`,逐轮标定。
- **V2(`V2_反向标定版/`)**:引入 `invert_dir` 方向反转,`single_tests/` 纯前进测试,仍逐轮标定。
- **V3(本目录)**:在 V2 基础上加 `sign` 参数,**去掉逐轮标定,四轮同步启动**。