# K230 调试工具链

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