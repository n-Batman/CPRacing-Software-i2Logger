import can
import csv
import fakeBLFdata
import cantools
import subprocess
import sys


from collections import Counter
from pathlib import Path

db = cantools.database.load_file('C:\\Users\\nlvat\\vscode-python-projects\\.vscode\\MotecLogGenerator\\i2LoggerProject\\can.dbc')
db.messages

log = fakeBLFdata.create_blf(Path(__file__).resolve().parent / "drive.blf", 2)

def create_csv(blf_path, csv_path="drive.csv"):
    """Decode BLF frames into fully numeric, forward-filled signal rows."""
    dbc_messages = {}
    seen_frame_ids = set()

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

    # Qualify signal names that occur in more than one DBC message so their
    # values are stored in separate CSV and MoTeC channels.
    signal_name_counts = Counter(
        signal.name
        for message in dbc_messages.values()
        for signal in message.signals
    )
    signal_columns = []
    column_lookup = {}
    for frame_id, message in dbc_messages.items():
        for signal in message.signals:
            if signal_name_counts[signal.name] > 1:
                column_name = f"{message.name}.{signal.name}"
            else:
                column_name = signal.name

            signal_columns.append(column_name)
            column_lookup[(frame_id, signal.name)] = column_name

    # DataLog removes a CSV channel as soon as it encounters a blank or other
    # nonnumeric value. Start unseen signals at zero, then hold their latest
    # decoded value until the next frame that updates them.
    current_values = {column_name: 0.0 for column_name in signal_columns}
    first_timestamp = None

    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["timestamp", *signal_columns],
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
                        decode_choices=False,
                    )
                except Exception as error:
                    print(
                        f"Skipping invalid frame at {frame.timestamp:.6f}: {error}"
                    )
                    continue

                for signal_name, value in decoded_signals.items():
                    column_name = column_lookup[
                        (frame.arbitration_id, signal_name)
                    ]
                    current_values[column_name] = value

                if first_timestamp is None:
                    first_timestamp = frame.timestamp

                writer.writerow(
                    {
                        "timestamp": f"{frame.timestamp - first_timestamp:.9f}",
                        **current_values,
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
