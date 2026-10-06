import can
import csv
import fakeBLFdata
import cantools
import subprocess
import sys


from pathlib import Path

db = cantools.database.load_file('C:\\Users\\nlvat\\vscode-python-projects\\.vscode\\MotecLogGenerator\\i2LoggerProject\\can.dbc')
db.messages

log = fakeBLFdata.create_blf(Path(__file__).resolve().parent / "drive.blf", 2)

def create_csv(blf_path, csv_path="drive.csv"):
    """Decode each BLF frame with the matching message from the DBC."""
    dbc_messages = {}
    seen_frame_ids = set()
    signal_names = []
    seen_signal_names = set()

    # Discover the messages present in the BLF before writing the CSV header.
    with can.BLFReader(blf_path) as log:
        for frame in log:
            if frame.arbitration_id in seen_frame_ids:
                continue
            seen_frame_ids.add(frame.arbitration_id)

            try:
                dbc_message = db.get_message_by_frame_id(frame.arbitration_id)
            except KeyError:
                # The DBC does not define this arbitration ID.
                continue

            dbc_messages[frame.arbitration_id] = dbc_message
            for signal in dbc_message.signals:
                if signal.name not in seen_signal_names:
                    signal_names.append(signal.name)
                    seen_signal_names.add(signal.name)

    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["timestamp", "channel", "id", *signal_names],
            extrasaction="ignore",
        )
        writer.writeheader()

        with can.BLFReader(blf_path) as log:
            for frame in log:
                dbc_message = dbc_messages.get(frame.arbitration_id)
                if dbc_message is None:
                    continue

                try:
                    decoded_signals = dbc_message.decode(
                        frame.data,
                        decode_choices=True,
                    )
                except Exception as error:
                    print(
                        f"Skipping invalid frame at {frame.timestamp:.6f}: {error}"
                    )
                    continue

                writer.writerow(
                    {
                        "timestamp": f"{frame.timestamp:.6f}",
                        "channel": frame.channel,
                        "id": f"0x{frame.arbitration_id:X}",
                        **decoded_signals,
                    }
                )

create_csv(
    Path(__file__).resolve().parent / "drive.blf",
    Path(__file__).resolve().parent / "drive.csv",
)


#change this to direct calls. 
subprocess.run(
    [
        sys.executable,
        str(Path(__file__).resolve().parent.parent / "motec_log_generator.py"),
        str(Path(__file__).resolve().parent / "drive.csv"),
        "CSV",
        "--output",
        "drive.ld",
    ],
    check=True,
)

