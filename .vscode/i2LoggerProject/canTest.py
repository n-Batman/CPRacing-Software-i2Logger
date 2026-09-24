import can
import csv
import fakeBLFdata
import cantools

from pathlib import Path

db = cantools.database.load_file('C:\\Users\\nlvat\\vscode-python-projects\\can.dbc')
db.messages

log = fakeBLFdata.create_blf(Path("drive.blf"), 2)

def create_csv(blf_path, dbc_message, csv_path = "drive.csv"):
    #Takes in the DBC message and BLF, and turns the BLF to a csv using DBC as collumns. 
    signal_names = [signal.name for signal in dbc_message.signals]

    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["timestamp", "channel", "id", *signal_names],
            extrasaction="ignore",
        )
        writer.writeheader()

        with can.BLFReader(blf_path) as log:
            for frame in log:

                if frame.arbitration_id != dbc_message.frame_id:
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
# probably use Can Bus Tools python to add DBC files to the can bus data. (adds units)
