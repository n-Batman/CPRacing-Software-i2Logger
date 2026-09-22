import can
import csv
import fakeBLFdata

from pathlib import Path

log = fakeBLFdata.create_blf(Path("drive.blf"), 1)

with can.BLFReader("drive.blf") as log:
    for message in log:
        print(
            f"{message.timestamp:.6f}  "
            f"channel={message.channel}  "
            f"id=0x{message.arbitration_id:X}  "
            f"data={message.data.hex(' ')}"
        )


with open("drive.csv", "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["timestamp", "channel", "id", "data"])
    with can.BLFReader("drive.blf") as log:
        for message in log:
            writer.writerow(
                [
                    f"{message.timestamp:.6f}",
                    message.channel,
                    f"0x{message.arbitration_id:X}",
                    message.data.hex(" "),
                ]
            )

