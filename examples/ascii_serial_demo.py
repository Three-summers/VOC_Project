"""基于 GenericSerialDevice 的 ASCII 串口示例。

运行方式：
    python examples/ascii_serial_demo.py --port /dev/ttyUSB0 --baudrate 115200

脚本会以换行符 (\n) 作为命令/响应分隔符，
向串口发送用户输入的 ASCII 文本，并打印收到的回显。"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from voc_app.loadport.serial_device import (
    GenericSerialCommand,
    GenericSerialDevice,
)


def build_ascii_frame(message: str = "") -> bytes:
    """根据用户输入构建 ASCII + 换行的命令帧。"""

    payload = (message or "").strip()
    return f"{payload}\n".encode("ascii")


def create_ascii_command(on_response):
    """创建一个命令定义，解析/回调全部为 ASCII 文本。"""

    return GenericSerialCommand(
        name="ascii_line",
        build_frame=build_ascii_frame,
        response_parser=lambda raw, _device: raw.decode("ascii", errors="ignore"),
        response_handler=lambda parsed, _device: on_response(parsed),
    )


class LineParser:
    """基于换行符的简单解析器。"""

    def __init__(self):
        self._buffer = bytearray()

    def __call__(self, chunk: bytes, device: GenericSerialDevice) -> None:
        self._buffer.extend(chunk)
        while b"\n" in self._buffer:
            line, _, remaining = self._buffer.partition(b"\n")
            self._buffer = bytearray(remaining)
            device.handle_response("ascii_line", line)


def main() -> int:
    parser = argparse.ArgumentParser(description="ASCII 串口交互示例")
    parser.add_argument(
        "--port", required=True, help="串口路径，如 /dev/ttyUSB0 或 COM3"
    )
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args()

    parser_fn = LineParser()

    # 这里可以根据回复来执行不同的回调函数
    def on_response(text: str) -> None:
        print(f"[RX] {text}")

    device = GenericSerialDevice(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        parser=parser_fn,
    )
    device.register_command(create_ascii_command(on_response))
    device.start()

    print("输入任意文本发送，输入 exit/quit 退出。")
    try:
        while True:
            try:
                user_input = input("ASCII> ")
            except EOFError:
                break
            if user_input.strip().lower() in {"exit", "quit"}:
                break
            if not user_input:
                continue
            device.send_command("ascii_line", message=user_input)
            # 休眠片刻，便于演示串口回显
            time.sleep(0.05)
    finally:
        device.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
