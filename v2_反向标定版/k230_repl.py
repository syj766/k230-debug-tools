# -*- coding: utf-8 -*-
"""K230 (CanMV) 串口 REPL 小工具。

用法:
    python k230_repl.py                # 默认 COM12，执行 print('hi')
    python k230_repl.py COM12          # 指定串口
    python k230_repl.py COM12 "1+1"    # 在板子上执行任意一条语句

原理: 通过 USB CDC 串口向板子发 Ctrl-C 中断当前程序, 进入 MicroPython REPL,
      再发送一条语句并回显板子的输出。
"""
import sys
import time

import serial


def drain(ser, idle=0.25, limit=3.0):
    """持续读到串口静默 idle 秒为止, 返回解码后的文本。"""
    buf = bytearray()
    start = time.time()
    deadline = start + idle
    while time.time() - start < limit and time.time() < deadline:
        n = ser.in_waiting
        if n:
            buf += ser.read(n)
            deadline = time.time() + idle
        else:
            time.sleep(0.02)
    return buf.decode("utf-8", "replace")


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM12"
    code = sys.argv[2] if len(sys.argv) > 2 else "print('hi')"

    try:
        ser = serial.Serial(port, 115200, timeout=0.1)
    except serial.SerialException as exc:
        print("打开 %s 失败: %s" % (port, exc))
        print("提示: 串口是独占的, 请先在 CanMV 插件/IDE 里断开连接。")
        return 1

    with ser:
        time.sleep(0.3)
        ser.reset_input_buffer()

        # Ctrl-C x2: 中断板子上正在运行的程序, 回到 >>> 提示符
        ser.write(b"\x03\x03")
        time.sleep(0.4)
        out = drain(ser, idle=0.3)
        print("---- 进入 REPL ----")
        print(out.strip() or "(无回显)")

        ser.write(b"\r\n")
        time.sleep(0.2)
        drain(ser, idle=0.2)

        print("---- 发送: %s ----" % code)
        ser.write(code.encode("utf-8") + b"\r\n")
        time.sleep(0.3)
        print(drain(ser, idle=0.4))

    return 0


if __name__ == "__main__":
    sys.exit(main())
