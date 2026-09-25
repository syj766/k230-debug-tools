# -*- coding: utf-8 -*-
"""把本地 MicroPython 文件通过 raw REPL 上传到 K230 执行并回显输出。

用法:
    python k230_run.py motor1_test.py
    python k230_run.py motor1_test.py COM12
    python k230_run.py motor_closed.py motor_manager.py test_manager.py COM12

支持多个文件: 按顺序拼接后一次性发送。除了最后一个文件, 前面的文件里
`if __name__ == "__main__":` 块会被自动去掉(库文件不触发自测),
只有最后一个文件的 __main__ 块会执行。

原理: Ctrl-C 中断当前程序 -> Ctrl-A 进 raw REPL -> 分块发送源码 -> Ctrl-D 执行。
      raw REPL 会把 stdout / stderr 分开回传, 便于区分 print 和异常。
"""
import re
import sys
import time

import serial

# Windows 控制台 stdout 常是 GBK, 板子输出的非 ASCII 字节会导致编码异常
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


def strip_main_block(src):
    """去掉 `if __name__ == '__main__':` 块, 避免拼接时触发库文件的自测。"""
    out = []
    skip = False
    for line in src.split("\n"):
        if line.startswith("if __name__"):
            skip = True
            continue
        if skip:
            if line[:1] in (" ", "\t") or not line.strip():
                continue            # 块内语句 / 空行
            skip = False            # 缩进结束
        out.append(line)
    return "\n".join(out)


def wait_for(ser, marker, timeout=10.0, echo=False):
    """读到出现 marker 结尾为止, 返回原始字节。

    echo=True 时边收边打印 —— 板子中途复位也能看到崩溃前的输出。
    """
    buf = bytearray()
    t0 = time.time()
    while time.time() - t0 < timeout:
        n = ser.in_waiting
        chunk = ser.read(n if n else 1)
        if chunk:
            buf += chunk
            if echo:
                s = chunk.decode("utf-8", "replace").replace("\x04", "")
                if s:
                    sys.stdout.write(s)
                    sys.stdout.flush()
            if bytes(buf).endswith(marker):
                return bytes(buf)
        else:
            time.sleep(0.01)
    return bytes(buf)


def main():
    args = sys.argv[1:]

    port = "COM12"
    if args and re.match(r"^COM\d+$", args[-1], re.IGNORECASE):
        port = args[-1]
        args = args[:-1]

    if not args:
        print(__doc__)
        return 1

    parts = []
    for i, path in enumerate(args):
        with open(path, "r", encoding="utf-8") as f:
            src = f.read().replace("\r\n", "\n")
        if i < len(args) - 1:
            src = strip_main_block(src)     # 库文件不触发自测
        parts.append(src)

    code = "\n\n".join(parts)
    if not code.endswith("\n"):
        code += "\n"

    try:
        ser = serial.Serial(port, 115200, timeout=0.05)
    except serial.SerialException as exc:
        print("打开 %s 失败: %s" % (port, exc))
        print("提示: 串口独占, 请先在 CanMV 插件里断开连接。")
        return 1

    with ser:
        time.sleep(0.3)
        ser.reset_input_buffer()

        # 1) 中断板子上正在运行的程序
        ser.write(b"\x03\x03")
        time.sleep(0.3)
        ser.reset_input_buffer()

        # 2) 进 raw REPL
        ser.write(b"\x01")
        head = wait_for(ser, b">", timeout=5.0)
        print("[REPL] %s" % head.decode("utf-8", "replace").strip())

        # 3) 分块发送源码
        data = code.encode("utf-8")
        print("[上传] %s  (%d 字节)" % (" + ".join(args), len(data)))
        for i in range(0, len(data), 128):
            ser.write(data[i:i + 128])
            time.sleep(0.01)

        # 4) Ctrl-D 触发执行
        time.sleep(0.2)
        ser.write(b"\x04")

        # 5) 收结果: OK <stdout> \x04 <stderr> \x04>
        #    实时回显 —— 板子中途复位也能看到崩溃前的输出
        raw = wait_for(ser, b"\x04>", timeout=120.0, echo=True)

        # 结束后退回普通 REPL, 方便后续交互
        ser.write(b"\x02")

    text = raw.decode("utf-8", "replace")
    if text.startswith("OK"):
        text = text[2:]
    parts = text.split("\x04")
    stderr = parts[1] if len(parts) > 1 else ""

    print()
    if stderr.strip():
        print("---- 异常/错误 ----")
        print(stderr.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
