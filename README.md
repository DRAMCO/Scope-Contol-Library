# Lab Instrument Control Utility

A Python utility for extracting waveform data from laboratory oscilloscopes and saving it in CSV format with metadata.

## Overview

The module provides a command-line interface to communicate with supported oscilloscopes via VISA (Virtual Instrument Software Architecture). It retrieves waveform data from one or more channels and saves the results to CSV files with relevant metadata.

### Supported Oscilloscopes

Currently, two oscilloscope models are supported:
- **Rigol DS1054** - 4-channel digital oscilloscope
- **Tektronix MSO2024** - Mixed-signal oscilloscope

## Installation

### Prerequisites

- Python 3.10 or later
- PyVISA library and appropriate VISA drivers for your oscilloscope

### Setup

1. Clone or download this repository to your system.

2. Add the repository to your Python system path. You can do this in several ways:

   **Option A: Add to PYTHONPATH environment variable**
   ```powershell
   $env:PYTHONPATH += ";C:\path\to\module"
   ```

   **Option B: Modify sys.path in your Python script**
   ```python
   import sys
   sys.path.insert(0, r'C:\path\to\module')
   ```

   **Option C: Install in development mode (recommended)**
   ```powershell
   cd C:\path\to\module
   pip install -e .
   ```

## Usage

### Command Line

Run the module using:

```powershell
py -m module_name get <instrument> <csv_file>
```

**Note:** Execute this command from the parent directory of the `module` package.

### Arguments

- **`instrument`** (required): The name of the instrument to query, as defined in `lab.py`. This name maps to the instrument's VISA address and configuration.
  
- **`csv_file`** (required): The output file path where waveform data will be saved in CSV format.

### Examples

```powershell
# Extract data from oscilloscope DR.SCP.01 and save to data.csv
py -m module_name get DR.SCP.01 data.csv

# Save to a specific directory
py -m module_name get DR.SCP.01 C:\data\measurements\scope_data.csv
```

## Data Format

### CSV File Structure

Output CSV files contain both metadata and waveform data:

1. **Metadata Header**: The first line contains the acquisition timestamp:
   ```
   #2026-05-26 14:30:45
   ```

2. **Metadata Lines**: Additional metadata is stored in lines starting with `#` in a semicolon and comma-delimited format:
   ```
   #xinc;0.00001,xzero;-0.0001,xref;0.0,channel1_scale;0.5
   ```

3. **Data**: Standard CSV format with channel data as columns:
   ```
   channel1,channel2,channel3
   0.123,-0.456,0.789
   0.124,-0.455,0.790
   ...
   ```

### Storage Optimization: Time Vector Handling

The module implements an efficient storage scheme for time information:

- **During Save**: The time column is not saved directly in the CSV. Instead, two parameters are extracted and stored in metadata:
  - `xzero`: The start time of the measurement
  - `xinc`: The time increment between samples
  
- **During Load**: When reading the CSV file, the time column is automatically reconstructed from `xzero` and `xinc` using:
  ```
  time = linspace(xzero, xzero + (xinc * num_samples), num_samples)
  ```

This approach reduces file size significantly while preserving all timing information needed to reconstruct the original time vector.

### Metadata Support

The module supports storing arbitrary metadata alongside measurements. Complex data types (lists, dictionaries, etc.) are automatically serialized and can be reconstructed when loading the file.

## Data Module (`data.py`)

The `data.py` module provides two primary functions:

### `save_csv(df, meta, filename)`

Saves a pandas DataFrame and metadata dictionary to a CSV file.

**Parameters:**
- `df`: pandas DataFrame containing waveform data
- `meta`: Dictionary of metadata to preserve
- `filename`: Output file path

**Features:**
- Automatically extracts and stores time information as `xzero` and `xinc`
- Handles complex data types using Python's `repr()` format
- Wraps metadata lines at 80 characters for readability
- Includes timestamp of save operation

### `load_csv(filename)`

Loads a CSV file saved by `save_csv()` and reconstructs the original data and metadata.

**Returns:**
- Tuple of (DataFrame, metadata dictionary)

**Features:**
- Automatically reconstructs the time column from `xzero` and `xinc`
- Deserializes complex metadata types using `ast.literal_eval()`
- Parses multiple metadata lines correctly

## Instrument Configuration

Instruments are defined in `lab.py` with the following structure:

```python
lab_instruments = {
    "instrument_name": {
        "visa_addr": "VISA_ADDRESS_STRING",
        "idn": "EXPECTED_IDENTIFICATION_STRING",
        "class": "ClassName"
    }
}
```

To add a new oscilloscope:

1. Obtain its VISA address using PyVISA's resource manager
2. Query its `*IDN?` identification string
3. Create an entry in `lab.py` with the appropriate class name (DS1054 or MSO2024)

## Technical Details

### VISA Communication

The module uses PyVISA for hardware communication, supporting multiple interfaces (USB, Ethernet, GPIB). The VISA address format varies by interface type and instrument.

### Binary Data Transfer

- **DS1054**: Uses 8-bit byte mode for efficient data transfer
- **MSO2024**: Uses 16-bit binary encoding (RIBinary format)

Data is automatically scaled using instrument calibration parameters (origin, reference, and increment values).

## Troubleshooting

### "Instrument not found" Error

Verify that:
- The instrument name exists in `lab.py`
- The oscilloscope is connected and powered on
- The VISA address is correct
- Required VISA drivers are installed

### Connection Issues

- Check USB/network connectivity to the oscilloscope
- Ensure the instrument is not in use by another application
- Verify VISA drivers match your oscilloscope model

### Import Errors

When running with `py -m`, ensure you're executing from the parent directory of the package, not from within it.

## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.

See the LICENSE file in the repository for full details. You are free to use, modify, and distribute this software under the terms of the GPLv3 license.

## Contact & Support

This software is maintained by the **Dramco Research Group** at KU Leuven.

- **Email**: info@dramco.be
- **Website**: www.dramco.be

For bug reports, feature requests, or technical support, please contact the Dramco team.
