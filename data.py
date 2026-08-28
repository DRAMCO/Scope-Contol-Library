import pandas as pd
import numpy as np
import ast
from typing import Tuple, Dict, Any
from datetime import datetime


def save_csv(df: pd.DataFrame, meta: Dict[str, Any], filename: str) -> None:
    """Save a DataFrame and metadata to a CSV file.

    The first line contains the current date and time as metadata (preceded by #).
    Metadata is stored as lines starting with '#' in the format:
    #key;value,key;value,key;value

    The DataFrame is saved as standard CSV below the metadata without an index column.
    Complex types like lists and dicts are stored using repr() and can be loaded back.

    If a 'time' column exists in the DataFrame, it is not saved. Instead, xzero and xinc
    are calculated and added to metadata if not already present.

    Args:
        df: pandas DataFrame to save
        meta: Dictionary of metadata to save
        filename: Output CSV file path
    """
    # Make a copy to avoid modifying the original dataframe
    df_save = df.copy()
    meta_save = meta.copy()

    # Handle time column: extract xzero and xinc if time column exists and not already in metadata
    if "time" in df_save.columns:
        if "xzero" not in meta_save and "xinc" not in meta_save:
            time_values = df_save["time"].values
            meta_save["xzero"] = float(time_values[0])
            meta_save["xinc"] = float((time_values[-1] - time_values[0]) / (len(time_values) - 1))
        # Remove time column from dataframe before saving
        df_save = df_save.drop(columns=["time"])

    with open(filename, "w") as f:
        # Write date and time as first metadata line (use from meta if provided, otherwise current)
        if "datetime" in meta_save:
            datetime_str = meta_save["datetime"]
            del meta_save["datetime"]
        else:
            datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"#{datetime_str}\n")

        # Build metadata key-value pairs
        meta_pairs = []
        for key, value in meta_save.items():
            # Use repr() to handle complex types like lists, dicts, etc.
            value_str = repr(value)
            meta_pairs.append(f"{key};{value_str}")

        # Distribute pairs across lines respecting line length limit
        current_line = "#"
        for pair in meta_pairs:
            # Test what the line would look like with this pair
            test_line = current_line + ("," if current_line != "#" else "") + pair

            # If adding this pair exceeds the limit and we already have content, start a new line
            if len(test_line) > 80 and current_line != "#":
                f.write(current_line + "\n")
                current_line = "#" + pair
            else:
                current_line = test_line

        # Write final metadata line
        if current_line != "#":
            f.write(current_line + "\n")

        # Write DataFrame without index, using explicit line terminator to avoid extra blank lines
        df_save.to_csv(f, index=False, lineterminator="\n")


def load_csv(filename: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load a DataFrame and metadata from a CSV file.

    The first line contains the date and time metadata (preceded by #).
    Metadata lines are expected to start with '#' in the format:
    #key;value,key;value,key;value

    Complex types are reconstructed using ast.literal_eval().

    If xzero and xinc are present in metadata, a 'time' column is constructed in the
    DataFrame using: df['time'] = np.linspace(xzero, xzero + (xinc * len(df)), len(df))

    Args:
        filename: Input CSV file path

    Returns:
        Tuple of (DataFrame, metadata dictionary)
    """
    meta = {}
    data_start_line = 0

    with open(filename, "r") as f:
        lines = f.readlines()

    # Parse metadata lines
    for i, line in enumerate(lines):
        if line.startswith("#"):
            # Remove the '#' and strip whitespace
            meta_line = line[1:].strip()

            # Extract datetime from first line if it only contains a datetime (no semicolon)
            if ";" not in meta_line:
                meta["datetime"] = meta_line
                data_start_line = i + 1
                continue

            # Parse key-value pairs separated by commas
            pairs = meta_line.split(",")
            for pair in pairs:
                if ";" in pair:
                    key, value_str = pair.split(";", 1)
                    key = key.strip()
                    value_str = value_str.strip()

                    # Try to evaluate the value back to its original type
                    try:
                        value = ast.literal_eval(value_str)
                    except (ValueError, SyntaxError):
                        # If evaluation fails, keep as string
                        value = value_str

                    meta[key] = value

            data_start_line = i + 1
        else:
            # Stop reading metadata at first non-# line
            break

    # Load DataFrame from remaining lines
    df = pd.read_csv(filename, skiprows=data_start_line)

    # Construct time column if xzero and xinc are in metadata
    if "xzero" in meta and "xinc" in meta:
        df["time"] = np.linspace(meta["xzero"], meta["xzero"] + (meta["xinc"] * len(df)), len(df))

    return df, meta


def fix_logic_file(filename: str):
    """Prepare Saleae logic analyzer CSV output for matplotlib/tikz plotting.

    Saleae logic analyzer exports only contain data points where signals change,
    which creates diagonal lines when plotted. This function inserts additional
    data points right before each transition to create steep vertical edges instead.

    For each row where any channel value changes from the previous row, a new row
    is inserted at time - 10ns containing the previous channel values. This ensures
    matplotlib/tikz plots show proper step functions instead of diagonal lines.

    Works with any number of Channel columns in the input CSV file.

    Args:
        filename: Path to the CSV file (with or without .csv extension)
    """
    # Handle filename with or without .csv extension
    if filename.endswith(".csv"):
        base_filename = filename.rsplit(".", maxsplit=1)[0]
    else:
        base_filename = filename
    
    # Read the CSV file
    df = pd.read_csv(f"{base_filename}.csv")
    dfc = df.copy()

    # Identify all Channel columns dynamically to support any number of channels.
    channel_cols = [col for col in df.columns if col.startswith("Channel")]

    # The time column name.
    time_col = "Time [s]"

    # Initialize previous values for all channels from the first row
    prev_values = {col: df[col].iloc[0] for col in channel_cols}

    # Iterate through each row and detect transitions.
    for i, row in dfc.iterrows():
        # Check if any channel has changed from the previous row.
        any_channel_changed = any(row[col] != prev_values[col] for col in channel_cols)

        if any_channel_changed:
            # Create a new row to insert before the transition with previous channel values.
            new_row_data = {time_col: row[time_col] - 10e-9}
            for col in channel_cols:
                new_row_data[col] = prev_values[col]

            # Insert the new row at a fractional index right before the current row.
            df.loc[i - 0.5] = pd.Series(new_row_data)

        # Update previous values for all channels for the next iteration.
        for col in channel_cols:
            prev_values[col] = row[col]

    # Sort by index to properly order the original and inserted rows.
    df = df.sort_index()

    # Save the fixed data to a new file.
    df.to_csv(f"{base_filename}-fixed.csv", index=False)
