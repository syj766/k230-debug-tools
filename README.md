﻿﻿# K230 调试工具链

K230 (工训项目) 串口调试 + 电机/底盘驱动开发脚本。

## 目录结构

```text
k230调试/
│
├── 【串口链路】电脑 ↔ COM12 ↔ K230
│   ├── k230_repl.py          发单条语句
│   ├── k230_run.py           执行本地文件(多文件拼接)
│   ├── k230_upload.py        烧录(CRC32 校验)
│   └── k230_monitor.py       实时监视
│
├── 【三层驱动框架】
│   ├── motor_closed.py       第一层: 单轮执行器
│   ├── motor_manager.py      第二三层: poll_all + Chassis
│   └── motor_test_lib.py     验证流程库
│
├── 【电机配置与测试】
│   ├── motor_fl_test.py      FL  61 / 14,15 / 17,27
│   ├── motor_rl_test.py      RL  46 / 36,37 / 40,41
│   ├── motor_rr_test.py      RR  47 / 3,4   / 5,6
│   ├── motor_fr_test.py      FR  52 / 32,33 / 34,35
│   └── test_chassis.py       四驱差速(待跑)
│
└── motor1_test.py            ← 最早的版本, 引脚(GPIO40/41)已过时
```

## 模块说明

### 串口链路(电脑 ↔ COM12 ↔ K230)
| 文件 | 作用 |
|------|------|
| `k230_repl.py` | 向 K230 发单条语句 |
| `k230_run.py` | 执行本地文件(多文件拼接连载) |
| `k230_upload.py` | 烧录文件(带 CRC32 校验) |
| `k230_monitor.py` | 实时监视串口输出 |

### 三层驱动框架
| 层 | 文件 | 作用 |
|----|------|------|
| 第一层 | `motor_closed.py` | 单轮执行器封装 |
| 第二三层 | `motor_manager.py` | `poll_all` 轮询 + `Chassis` 底盘 |
| 验证库 | `motor_test_lib.py` | 电机验证流程封装 |

### 电机配置与测试
电机测试脚本均标注了`(编码器频道 / 霍尔A,B / PWM 引脚)`：

| 文件 | 轮位 | 频/脚位 |
|------|------|---------|
| `motor_fl_test.py` | FL 左前 | 61 / 14,15 / 17,27 |
| `motor_rl_test.py` | RL 左后 | 46 / 36,37 / 40,41 |
| `motor_rr_test.py` | RR 右后 | 47 / 3,4 / 5,6 |
| `motor_fr_test.py` | FR 右前 | 52 / 32,33 / 34,35 |
| `test_chassis.py` | 四驱差速 | 待跑 |

### 早期版本
- `motor1_test.py` —— 最早的电机测试版本,引脚(GPIO40/41)已过时,保留作参考。

## 三层驱动架构(总体思路,不分版本)

三层的职责划分:

- **底层｜轮子层**:`Encoder + FF + PI` —— 确保**"这个轮子真的跑 500Hz"**(每个轮子跑得准)
- **中层｜底盘层**:`poll_all + Chassis` —— 确保**"四个轮子协调起来跑"**(同时测、同时控)
- **上层｜应用层**:`前进 / 后退 / 转弯 / 掉头` —— 只描述**"我想让车怎么动"**

### 第一层:`motor_closed.py` — 单轮闭环

**文件结构**

```
PIController        ←  位置式 PI (只有 P 和 I,没有 D)
ClosedMotor         ←  单电机: 解码 + 驱动 + 控制
_QUAD               ←  正交解码查找表(16 个值)
```

**① 正交解码** — 霍尔编码器输出 A、B 两相方波,4 种状态:

```
A: 0→1→1→0→0
B: 0→0→1→1→0
状态序列: 00 → 01 → 11 → 10 → 00  (正转)
状态序列: 00 → 10 → 11 → 01 → 00  (反转)
```

`_QUAD` 是 16 值查找表:`_QUAD[(旧状态<<2)|新状态]` → +1 正转一步、-1 反转一步、0 没变或抖动。

**② 轮询采样 `poll(ms)`** — 没有中断(因 K230 的 `Pin.irq` 会崩板),改用主循环轮询:

```
while 时间没到 ms:
    读 A、B 引脚 → 组装状态
    查 _QUAD 表 → count +/- 1
```

阻塞 ms 毫秒,返回脉冲数。

**③ 方向标定 `calibrate_sign()`** — 正转 30% duty,数 300ms 脉冲:

```
count > 0  →  sign = +1   编码器和驱动方向一致
count < 0  →  sign = -1   相反,后续乘 -1 修正
count = 0  →  编码器没信号
```

**④ PI 控制 `PIController.update(error)`**:

```
error = target - speed          ← 你想要的 - 实际跑的
I += error                      ← 积分累加(消灭稳态误差)
I = clamp(I, ±integral_limit)   ← 防积分饱和
out = kp*error + ki*I           ← P项 + I项
out = clamp(out, ±output_limit) ← PI输出限幅(±20%)
```

**⑤ 前馈 + PI = 总输出 `apply_count()`**:

```
hz_raw = count/时间 → 实测速度
speed  = α·hz_raw + (1-α)·speed   ← 低通滤波,去毛刺
out = ff × target + pi.update(target - speed)
       ↑前馈猜一个      ↑PI微调
```

**⑥ PWM 输出 `drive(duty)`**:

```
duty > 0:  IN1=H  IN2=L  →  正转
duty < 0:  IN1=L  IN2=H  →  反转
duty = 0:  IN1=L  IN2=L  →  滑行
刹车:      IN1=H  IN2=H  →  短路制动
```

### 第二层:`motor_manager.py` — 共享采样

`poll_all()` 一次循环同时看四个编码器:

```
states = [读A, 读B, 读C, 读D]
while 窗口没到:
    for 每个电机:
        读状态 → 变了就查表计数
返回 [count_A, count_B, count_C, count_D]
```

**为什么不能各采各的?** 四个 `update(20ms)` 串行 = 80ms/周期,太慢;共享窗口一次循环看四轮编码器,20ms 搞定。

### 第三层:`Chassis` — 差速底盘

```
chassis = Chassis([FL, RL], [FR, RR])   # 左两轮 / 右两轮
chassis.set_velocity(500, 500)   # 直行: 左500 右500
chassis.turn(500, 200)           # 左转: 左转
while True:
    chassis.update()   # = poll_all + 4个 apply_count
```

### 一张图总结

```
你调用 chassis.turn(500, 200)
        ↓
  set_velocity(300, 700)     ← 给每个 ClosedMotor 设 target
        ↓
  update() → poll_all(20ms)  ← 四轮同时数脉冲
        ↓
  apply_count(count, 20ms) × 4
        ↓
  ff*target + pi.update(error) → duty
        ↓
  drive(duty) → IN1/IN2/PWM  →  轮子转
```

## 版本索引

- **第一版**:本目录(根)文件,`ClosedMotor.__init__` 无 `invert_dir`。
- **第二版**:[`v2_反向标定版/`](v2_%E5%8F%8D%E5%90%91%E6%A0%87%E5%AE%9A%E7%89%88/) —— 新增 `invert_dir` 单电机方向反转,并推荐优先使用 `single_tests/` 下的纯前进测试文件。详细说明见该目录下的 `README.md`。


