from pathlib import Path
import fakeBLFdata
import canTest
from canTest import create_csv

project_dir = Path(__file__).resolve().parent
dbc_path = project_dir / "can.dbc"
blf_path = project_dir / "drive.blf"
csv_path = project_dir / "drive.csv"

frames_written = fakeBLFdata.create_blf(
    output=blf_path,
    repeat=10,
    dbc_path=dbc_path,
)

create_csv(blf_path, csv_path)

print(f"Generated {frames_written} CAN frames")
print(f"BLF output: {blf_path}")
print(f"CSV output: {csv_path}")