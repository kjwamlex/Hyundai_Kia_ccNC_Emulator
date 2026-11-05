#!/usr/bin/env python3
"""Capture the actual QEMU display through a local QMP Unix socket."""
import argparse
import json
import socket
import time
from pathlib import Path


def command(stream, name, arguments=None):
    request = {"execute": name}
    if arguments is not None:
        request["arguments"] = arguments
    stream.write(json.dumps(request).encode() + b"\n")
    while True:
        data = stream.readline()
        if not data:
            raise RuntimeError("QEMU closed its QMP socket")
        response = json.loads(data)
        if "error" in response:
            raise RuntimeError(response["error"])
        if "return" in response:
            return response["return"]


def screenshot(socket_path, output):
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(10)
        connection.connect(str(socket_path))
        with connection.makefile("rwb", buffering=0) as stream:
            json.loads(stream.readline())
            command(stream, "qmp_capabilities")
            command(stream, "screendump", {"filename": str(output), "format": "png"})
    return output


def click(socket_path, x, y, width=1920, height=720):
    """Inject a real tablet click through QEMU, in framebuffer coordinates."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(10)
        connection.connect(str(socket_path))
        with connection.makefile("rwb", buffering=0) as stream:
            json.loads(stream.readline())
            command(stream, "qmp_capabilities")
            command(stream, "input-send-event", {"events": [
                {"type": "abs", "data": {"axis": "x", "value": round(x * 32767 / (width - 1))}},
                {"type": "abs", "data": {"axis": "y", "value": round(y * 32767 / (height - 1))}}]})
            command(stream, "input-send-event", {"events": [
                {"type": "btn", "data": {"down": True, "button": "left"}}]})
            time.sleep(0.15)
            command(stream, "input-send-event", {"events": [
                {"type": "btn", "data": {"down": False, "button": "left"}}]})


def send_key(socket_path, key):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(10)
        connection.connect(str(socket_path))
        with connection.makefile("rwb", buffering=0) as stream:
            json.loads(stream.readline())
            command(stream, "qmp_capabilities")
            command(stream, "send-key", {"keys": [{"type": "qcode", "data": key}], "hold-time": 100})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("socket", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(screenshot(args.socket, args.output))
