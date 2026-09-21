# -*- coding: utf-8 -*-
"""把本地文件烧录(写入)到 K230 板子的文件系统。

用法:
    python k230_upload.py motor1_test.py                     # -> /data/motor1_test.py
    python k230_upload.py motor1_test.py /data/xxx.py         # 指定板子路径
    python k230_upload.py motor1_test.py /data/xxx.py COM12   # 指定串口

原理: Ctrl-A 进 raw REPL, 源码 base64 分块追加写入, 最后用 CRC32 校验完整性。
      base64 可避免源码里的控制字符(\\x03 / \\x04)打断 REPL 协议。
"""
import base64
import os
import sys
import time
import zlib

import serial

CHUNK = 192          # 每块原始字节数(编码后约 256 字符, 保证 raw REPL 单行安全)
BAUD = 115200


def wait_for(ser, marker, timeout=10.0):
    buf = bytearray()
    t0 = time.time()
    while time.time() - t0 < timeout:
        n = ser.in_waiting
        chunk = ser.read(n if n else 1)
        if chunk:
            buf += chunk
            if bytes(buf).endswith(marker):
                return bytes(buf)
        else:
            time.sleep(0.005)
    return bytes(buf)


class Board:
    def __init__(self, port):
        self.ser = serial.Serial(port, BAUD, timeout=0.05)
        time.sleep(0.3)
        self.ser.reset_input_buffer()
        self.ser.write(b"\x03\x03")      # Ctrl-C x2: 中断板上正在跑的程序
        time.sleep(0.3)
        self.ser.reset_input_buffer()

    def enter_raw(self):
        self.ser.write(b"\x01")          # Ctrl-A
        wait_for(self.ser, b">", timeout=3.0)

    def exit_raw(self):
        self.ser.write(b"\x02")          # Ctrl-B

    def run(self, code, timeout=8.0):
        """在 raw REPL 中执行一行代码, 返回 (stdout, stderr)。"""
        self.ser.write(code.encode("utf-8"))
        time.sleep(0.03)
        self.ser.write(b"\x04")          # Ctrl-D: 执行
        raw = wait_for(self.ser, b"\x04>", timeout=timeout)
        text = raw.decode("utf-8", "replace")
        if text.startswith("OK"):
            text = text[2:]
        parts = text.split("\x04")
        out = parts[0].strip() if parts else ""
        err = parts[1].strip() if len(parts) > 1 else ""
        return out, err

    def close(self):
        self.ser.close()


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1

    local = args[0]
    remote = args[1] if len(args) > 1 else "/data/" + os.path.basename(local)
    port = args[2] if len(args) > 2 else "COM12"

    with open(local, "rb") as f:
        data = f.read()
    local_crc = zlib.crc32(data) & 0xFFFFFFFF
    chunks = [data[i:i + CHUNK] for i in range(0, len(data), CHUNK)]

    try:
        board = Board(port)
    except serial.SerialException as exc:
        print("打开 %s 失败: %s" % (port, exc))
        print("提示: 串口独占, 请先在 CanMV 插件里断开连接。")
        return 1

    try:
        board.enter_raw()

        out, err = board.run("f=open('%s','wb');f.close()" % remote)
        if err:
            print("无法创建 %s: %s" % (remote, err))
            return 1

        print("烧录 -> %s  (%d 字节 / %d 块)" % (remote, len(data), len(chunks)))
        for i, chunk in enumerate(chunks, 1):
            b64 = base64.b64encode(chunk).decode("ascii")
            code = ("import base64;f=open('%s','ab');"
                    "f.write(base64.b64decode('%s'));f.close()" % (remote, b64))
            out, err = board.run(code)
            if err:
                print("\n第 %d 块写入失败: %s" % (i, err))
                return 1
            sys.stdout.write("\r  进度 %d/%d" % (i, len(chunks)))
            sys.stdout.flush()
        print()

        # ---------- 校验 ----------
        out, err = board.run(
            "import binascii;print(binascii.crc32(open('%s','rb').read()))" % remote)
        if not err:
            board_crc = int(out.splitlines()[-1]) & 0xFFFFFFFF
            if board_crc == local_crc:
                print("校验通过  CRC32=%08X  板子文件完整" % local_crc)
            else:
                print("校验失败! 本地=%08X 板子=%08X" % (local_crc, board_crc))
                return 1
        else:
            # 固件没有 binascii 时退回长度校验
            out, err = board.run("import os;print(os.stat('%s')[6])" % remote)
            size = int(out.splitlines()[-1])
            if size == len(data):
                print("校验通过  长度 %d 字节一致" % size)
            else:
                print("校验失败! 本地=%d 板子=%d" % (len(data), size))
                return 1
    finally:
        board.exit_raw()
        board.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
