import argparse
from . import inst

from .lab import lab_instruments
from .data import save_csv


def get_waveform(args):
    """Extract waveform data from an instrument and save to CSV."""
    # Look up the instrument in the lab dictionary
    if args.instrument not in lab_instruments:
        raise ValueError(f"Instrument '{args.instrument}' not found in lab.py")

    instrument_config = lab_instruments[args.instrument]
    visa_addr = instrument_config["visa_addr"]
    idn = instrument_config["idn"]
    class_name = instrument_config["class"]

    # Instantiate the instrument and retrieve waveform data
    instrument_class = getattr(inst, class_name)
    instrument = instrument_class(visa_addr, idn)
    df, meta = instrument.get()

    # Write to CSV
    save_csv(df, meta, args.csv_file)
    print(f"Data written to: {args.csv_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lab instrument control utility")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add 'get' subcommand
    get_parser = subparsers.add_parser("get", help="Extract waveform from an instrument")
    get_parser.add_argument("instrument", help="Instrument name from lab.py")
    get_parser.add_argument("csv_file", help="Output CSV file path")
    get_parser.set_defaults(func=get_waveform)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
