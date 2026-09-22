#!/usr/bin/env python3
"""Create a small Vector BLF fixture containing deterministic CAN traffic.

Install the only dependency with:
    python -m pip install python-can

Example:
    python make_fake_blf.py fake_can.blf
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from can import Message
from can.io.blf import BLFWriter


def make_message(
    arbitration_id: int,
    data: bytes,
    timestamp: float,
    channel: int = 0,
) -> Message:
    """Return one ordinary 11-bit, classic-CAN data frame."""
    return Message(
        arbitration_id=arbitration_id,
        data=data,
        timestamp=timestamp,
        channel=channel,
        is_extended_id=False,
        is_fd=False,
    )


def create_blf(output: Path, repeat: int = 10) -> None:
    """Write `repeat` simple cycles of three CAN signals to *output*."""
    if repeat < 1:
        raise ValueError("repeat must be at least 1")

    output.parent.mkdir(parents=True, exist_ok=True)
    start = datetime.now(timezone.utc)

    # BLFWriter owns the file and must be stopped so it can finish the file
    # header and write any buffered log container data.
    writer = BLFWriter(str(output), append=False)
    try:
        for cycle in range(repeat):
            base = start + timedelta(milliseconds=100 * cycle)
            timestamp = base.timestamp()

            # An engine-speed-like signal, little-endian uint16 at byte 0.
            rpm = 800 + cycle * 25
            writer.on_message_received(
                make_message(0x100, rpm.to_bytes(2, "little") + b"\x00" * 6, timestamp)
            )

            # A vehicle-speed-like signal: 0.1 km/h units in byte 0.
            speed_tenths = min(255, cycle * 12)
            writer.on_message_received(
                make_message(0x101, bytes([speed_tenths]) + b"\x00" * 7, timestamp + 0.010)
            )

            # A status counter used to make frames visibly change over time.
            writer.on_message_received(
                make_message(0x200, bytes([cycle & 0xFF, 0x01, 0x00]), timestamp + 0.020)
            )
    finally:
        writer.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a simple fake CAN BLF file.")
    parser.add_argument("output", nargs="?", default="fake_can.blf", help="output .blf path")
    parser.add_argument("--repeat", type=int, default=10, help="number of 100 ms traffic cycles")
    args = parser.parse_args()

    output = Path(args.output)
    create_blf(output, args.repeat)
    print(f"Wrote {output} ({args.repeat * 3} CAN frames)")


if __name__ == "__main__":
    main()