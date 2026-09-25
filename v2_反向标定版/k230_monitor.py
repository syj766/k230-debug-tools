# -*- coding: utf-8 -*-
"""实时监视 K230 串口输出(并可手动发命令)。

用法:
    python k230_monitor.py            # 默认 COM12
    python k230_monitor.py COM12

退出: Ctrl-C

注意: 串口独占, 运行本脚本时 VSCode 的 CanMV 插件必须断开连接。
"""
import sys
import threading

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM12"


def reader(ser, stop):
    while not stop.is_set():
        try:
            data = ser.read(4096)
        except Exception:
            return
        if data:
            sys.stdout.write(data.decode("utf-8", "replace"))
            sys.stdout.flush()


def main():
    try:
        ser = serial.Serial(PORT, 115200, timeout=0.1)
    except serial.SerialException as exc:
        print("打开 %s 失败: %s" % (PORT, exc))
        print("提示: 请先在 CanMV 插件里断开连接。")
        return 1

    print("[已连接 %s] 直接输入命令回车发给板子, Ctrl-C 退出。" % PORT)

    stop = threading.Event()
    threading.Thread(target=reader, args=(ser, stop), daemon=True).start()

    try:
        for line in sys.stdin:
            ser.write(line.rstrip("\r\n").encode("utf-8") + b"\r\n")
    except KeyboardInterrupt:
        print("\n[断开]")
    finally:
        stop.set()
        ser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
