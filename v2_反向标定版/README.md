# v2 —— 反向标定版

本目录是第二版(反向标定版)。第一版原始文件保留在仓库根目录,**本版不覆盖任何第一版文件**,以独立子目录并存。

## 核心改动:`invert_dir` 单电机方向反转

在 `motor_closed.py` 的 `ClosedMotor.__init__` 增加了一个参数:

```python
def __init__(self, ..., invert_dir=False):
    ...
    if invert_dir:
        pin_in1, pin_in2 = pin_in2, pin_in1   # 两行,在创建 Pin 对象之前内部交换
```

### 目的

RL(左后)、RR(右后)硬件接线无误,但同一个 `IN1=H, IN2=L` 信号
让 FL/FR 前进、让 RL/RR 后退。**不改硬件、不改引脚数字**,而是显式标记
"这两个电机方向反了",从而统一前进方向。

### 逻辑

目标: 四轮前进 → 代码 `set_target(+300)` → `drive(duty>0)` → `IN1=H, IN2=L`

| 电机 | invert_dir | 效果 |
|------|-----------|------|
| FL / FR | `False`(默认) | `IN1=H, IN2=L` → TB6612 正转 → **前进** ✅ |
| RL / RR | `True` | `__init__` 内部交换 `pin_in1 ↔ pin_in2`,`drive()` 写的 `self.in1=self.in2` 实际 GPIO 对调,TB6612 收到与 FL/FR 相同的信号 → **前进** ✅ |

### 为什么这样做

- **不改硬件**:不动线。
- **不偷偷改引脚数字**:不把 RI 的 `IN1` 伪装成别人的引脚,而是显式语义 "此电机方向反了"。
- **透明**:交换发生在 `__init__` 创建 Pin 对象之前。`drive() / brake() / calibrate_sign() / PI 控制` 一行未动,对后续所有逻辑完全透明。

## 电机测试文件:根目录 vs single_tests/

本版共有两组电机测试文件,建议**优先用 `single_tests/` 里的那组**:

| 文件 | 位置 | 功能 |
|------|------|------|
| `motor_fl_test.py` | 根目录 | 四轮单测(校准 + 跟踪 + 负载) |
| `motor_rl_test.py` | 根目录 | 同上 |
| `motor_rr_test.py` | 根目录 | 同上 |
| `motor_fr_test.py` | 根目录 | 同上 |
| `single_tests/test_fl.py` | 子目录 | 四轮单测(纯前进) |
| `single_tests/test_rl.py` | 子目录 | 同上 |
| `single_tests/test_rr.py` | 子目录 | 同上 |
| `single_tests/test_fr.py` | 子目录 | 同上 |

另外还有 `motor1_test.py`(早期版本,引脚已过时)。

### 为什么 `single_tests/` 更好

**根目录那 4 个有两个问题:**

1. **只初始化一个电机就拉 STBY**,其他三轮引脚浮空会误转。
2. **依赖 `motor_test_lib.py` 的 `verify()`**,多一层依赖。

**`single_tests/` 的 4 个更干净:**

1. **初始化全部 8 个 IN 脚 + 4 个 PWM 脚为安全态再拉 STBY**,避免其他轮误转。
2. 纯前进测试,`300/500/700/0 Hz`。
3. **支持 `invert_dir`**。

## 本版新增文件

| 文件 | 说明 |
|------|------|
| `test_forward.py` | 四轮同步前进测试,调用 `MotorManager` 统一采样,`MOTORS` 表中标记 RL/RR 为 `True` |
| `single_tests/test_fl.py` | FL(左前)单轮前进测试模板 |
| `single_tests/test_fr.py` | FR(右前)单轮前进测试 |
| `single_tests/test_rl.py` | RL(左后)单轮前进测试,`invert_dir=True` |
| `single_tests/test_rr.py` | RR(右后)单轮前进测试,`invert_dir=True` |

## 接线(四轮差分)

```
FL  61 / 14,15 / 17,27      RL  46 / 36,37 / 40,41
RR  47 / 3,4   / 5,6        FR  52 / 32,33 / 34,35
STBY = GPIO2 (共用)
```

## 与第一版的区别

- 第一版(仓库根目录):`ClosedMotor.__init__` 无 `invert_dir`,若有反向电机需要手动改引脚或换线。
- 第二版(本目录):支持 `invert_dir` 参数化方向反转,RL/RR 显式标记为 `True`,其余逻辑不变。