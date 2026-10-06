#!/usr/bin/env python3
"""Generate deterministic BLF traffic from every message in ``can.dbc``."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cantools
from can import Message
from can.io.blf import BLFWriter


HERE = Path(__file__).resolve().parent
DEFAULT_DBC_PATH = HERE / "can.dbc"


def _raw_value(signal: Any, cycle: int, signal_index: int, frame_id: int) -> int:
    """Return a changing integer that fits in the signal's raw bit field."""
    seed = frame_id + signal_index * 17 + cycle * 31

    if signal.length == 1:
        return seed % 2

    if signal.is_signed:
        limit = min((1 << (signal.length - 1)) - 1, 1000)
        return (seed % (2 * limit + 1)) - limit

    limit = min((1 << signal.length) - 1, 2000)
    return seed % (limit + 1)


def _signal_values(dbc_message: Any, cycle: int) -> dict[str, int]:
    """Build raw values for the active signals in a DBC message.

    Walking ``signal_tree`` also makes the generator work with multiplexed DBC
    messages: one valid multiplexer branch is selected on each cycle.
    """
    signals = {signal.name: signal for signal in dbc_message.signals}
    signal_indexes = {
        signal.name: index for index, signal in enumerate(dbc_message.signals)
    }
    values: dict[str, int] = {}

    def visit(nodes: list[Any]) -> None:
        for node in nodes:
            if isinstance(node, str):
                signal = signals[node]
                values[node] = _raw_value(
                    signal,
                    cycle,
                    signal_indexes[node],
                    dbc_message.frame_id,
                )
                continue

            for multiplexer_name, branches in node.items():
                branch_ids = sorted(branches)
                branch_id = branch_ids[cycle % len(branch_ids)]
                values[multiplexer_name] = branch_id
                visit(branches[branch_id])

    visit(dbc_message.signal_tree)
    return values


def _make_can_message(
    dbc_message: Any,
    payload: bytes,
    timestamp: float,
    channel: int,
) -> Message:
    """Create a python-can message with the frame properties from the DBC."""
    return Message(
        arbitration_id=dbc_message.frame_id,
        data=payload,
        timestamp=timestamp,
        channel=channel,
        is_extended_id=dbc_message.is_extended_frame,
        is_fd=dbc_message.length > 8,
        check=True,
    )


def create_blf(
    output: str | Path,
    repeat: int = 1,
    dbc_path: str | Path = DEFAULT_DBC_PATH,
    cycle_period: float = 0.1,
    channel: int = 0,
) -> int:
    """Write fake data for every DBC message to a BLF file.

    ``output`` and ``repeat`` retain the original function's calling convention,
    so ``create_blf(Path("drive.blf"), 2)`` continues to work.  A different DBC
    can be supplied with the ``dbc_path`` keyword argument.

    Values are encoded as raw integers.  This is intentional because ``can.dbc``
    contains many signals with physical bounds recorded as ``[0|0]`` even though
    their raw bit fields accept other values.

    Returns the number of frames written.
    """
    if repeat < 1:
        raise ValueError("repeat must be at least 1")
    if cycle_period <= 0:
        raise ValueError("cycle_period must be greater than zero")

    output = Path(output)
    dbc_path = Path(dbc_path)
    if not dbc_path.is_file():
        raise FileNotFoundError(f"DBC file does not exist: {dbc_path}")

    database = cantools.database.load_file(dbc_path)
    if not database.messages:
        raise ValueError(f"DBC file contains no messages: {dbc_path}")

    output.parent.mkdir(parents=True, exist_ok=True)
    start_timestamp = datetime.now(timezone.utc).timestamp()
    frame_spacing = cycle_period / len(database.messages)
    frames_written = 0

    writer = BLFWriter(str(output), append=False)
    try:
        for cycle in range(repeat):
            for message_index, dbc_message in enumerate(database.messages):
                payload = dbc_message.encode(
                    _signal_values(dbc_message, cycle),
                    scaling=False,
                    padding=False,
                    strict=True,
                )
                timestamp = (
                    start_timestamp
                    + cycle * cycle_period
                    + message_index * frame_spacing
                )
                writer.on_message_received(
                    _make_can_message(dbc_message, payload, timestamp, channel)
                )
                frames_written += 1
    finally:
        writer.stop()

    return frames_written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create fake CAN BLF data from every message in a DBC file."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=HERE / "drive.blf",
        type=Path,
        help="output .blf path (default: i2LoggerProject/drive.blf)",
    )
    parser.add_argument(
        "--dbc",
        default=DEFAULT_DBC_PATH,
        type=Path,
        help="input DBC path (default: i2LoggerProject/can.dbc)",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="number of copies to generate for each DBC message (default: 1)",
    )
    parser.add_argument(
        "--cycle-period",
        type=float,
        default=0.1,
        metavar="SECONDS",
        help="seconds between the start of each traffic cycle",
    )
    parser.add_argument("--channel", type=int, default=0, help="CAN channel number")
    args = parser.parse_args()

    frame_count = create_blf(
        args.output,
        repeat=args.repeat,
        dbc_path=args.dbc,
        cycle_period=args.cycle_period,
        channel=args.channel,
    )
    print(f"Wrote {args.output} ({frame_count} frames from {args.dbc})")


if __name__ == "__main__":
    main()
