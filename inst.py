import pyvisa
import pandas as pd
import numpy as np


class VisaInstrument:
    """Generic Visa controlled instrument."""

    def __init__(self, addr):
        self.rm = pyvisa.ResourceManager()

        self.visa_interface = self.rm.open_resource(addr)

    def write(self, cmd: str, termination: str | None = None, encoding: str | None = None) -> int:
        return self.visa_interface.write(cmd)

    def query(self, cmd: str, delay: float | None = None) -> str:
        return self.visa_interface.query(cmd, delay).strip()

    def read(self, termination: str | None = None, encoding: str | None = None) -> str:
        return self.visa_interface.read(termination, encoding)


class ScpiInstrument(VisaInstrument):
    """Instrument using the SCPI language for communication."""

    def __init__(self, addr, idn):
        super().__init__(addr)

        self.idn = idn
    
    def reset(self):
        self.write("*RST")

    def check_idn(self):
        idn_response = self.query("*IDN?")

        if idn_response != self.idn:
            raise ValueError(
                f"Received identification string `{idn_response}` does not match the expected one `{self.idn}`."
            )


class DS1054(ScpiInstrument):
    """Class for the Rigol DS1054 oscilloscope."""

    def get(self):
        """Get the data from the oscilloscope.

        The data is returned in a pandas DataFrame.
        """
        # We transfer the waveform from memory in byte mode.
        self.write("waveform:mode raw")
        self.write("waveform:format byte")
        self.write("waveform:start 1")
        self.write("waveform:stop 15000")

        # Get all the relevant metadata.
        xorigin = float(self.query("waveform:xorigin?"))
        xref = float(self.query("waveform:xreference?"))
        xinc = float(self.query("waveform:xincrement?"))

        # Check which channels are enabled.
        channels = []
        for ch in range(1, 5):
            enabled = int(self.query(f"channel{ch}:display?"))
            if enabled != 0:
                channels.append(f"channel{ch}")

        data = []
        # Get the data for all the active channels.
        for ch in channels:
            self.write(f"waveform:source {ch}")
            yorigin = float(self.query("waveform:yorigin?"))
            yref = float(self.query("waveform:yreference?"))
            yinc = float(self.query("waveform:yincrement?"))
            ch_data = self.visa_interface.query_binary_values("waveform:data?", datatype="c", is_big_endian=True)

            ch_data = [(int.from_bytes(x) - yorigin - yref) * yinc for x in ch_data]
            data.append(ch_data)

        # Transpose the data
        data = [list(i) for i in zip(*data)]
        df = pd.DataFrame(data, columns=channels)

        # Add time column based on xinc and xzero
        df["time"] = np.linspace(xorigin, xorigin + (xinc * len(df)), len(df))

        meta = {"xinc": xinc, "xzero": xorigin, "xref": xref}
        return df, meta


class MSO2024(ScpiInstrument):
    """Class for the Tektronix MSO2024 mixed-signal oscilloscope."""

    def get(self):
        """Get the data from the oscilloscope.

        The data is returned in a pandas DataFrame.
        """
        # Configure data encoding for binary transfer
        self.write("data:encdg ribinary")
        self.write("wfmoutpre:byt_nr 2")

        # Check which channels are enabled
        channels = []
        for ch in range(1, 5):
            enabled = int(self.query(f"SELect:CH{ch}?"))
            if enabled != 0:
                channels.append(f"CH{ch}")

        data = []
        xinc = 0.0
        xzero = 0.0
        # Get the data for all active channels
        for ch in channels:
            # Set source for waveform transfer
            self.write(f"DATA:SOUrce {ch}")

            # Get horizontal scale information
            xinc = float(self.query("wfmoutpre:xincr?"))
            xzero = float(self.query("wfmoutpre:xzero?"))

            # Extract Y-axis scaling from preamble
            yorigin = float(self.query("wfmoutpre:yoff?"))
            yinc = float(self.query("wfmoutpre:ymult?"))

            # Request waveform data
            ch_data = self.visa_interface.query_binary_values("CURVe?", datatype="h", is_big_endian=True)

            # Convert byte data to voltage values
            ch_data = [(x - yorigin) * yinc for x in ch_data]
            data.append(ch_data)

        # Transpose the data to have samples as rows and channels as columns
        data = [list(i) for i in zip(*data)]
        df = pd.DataFrame(data, columns=channels)

        # Add time column based on xinc and xzero
        df["time"] = np.linspace(xzero, xzero + (xinc * len(df)), len(df))

        meta = {"xinc": xinc, "xzero": xzero}
        return df, meta

class K2425(ScpiInstrument):
    """Class for the Keithley 2425 SMU."""
    def get(self):
        """Get the data currently in the output buffer.

        The data is returned in a pandas DataFrame.
        """
        # Return absolute timestamps.
        self.write("trace:tstamp:format absolute")
        self.write("format:elements voltage,current,time")
        # The RS232 interface only allows ASCII.
        self.write("format:data ascii")

        # A fetch will return the last measured readings.
        # The format should be: voltage,current,time
        readings = self.query("fetch?")
        readings_array = readings.split(',')
        voltage = map(float, readings_array[::3])
        current = map(float, readings_array[1::3])
        time = map(float, readings_array[2::3])

        data = [list(i) for i in zip(*[voltage, current, time])]
        df = pd.DataFrame(data, columns=["voltage", "current", "time"])

        xinc = 0.0
        if len(df) > 1:
            xinc = df['time'].iloc[1] - df['time'].iloc[0]
        xzero = df['time'].iloc[0]
        
        meta = {"xinc": xinc, "xzero": xzero}

        return df, meta
