import tkinter as tk
from tkinter import filedialog
import pandas as pd
from datetime import datetime
import numpy as np
from scipy.interpolate import interp1d
from scipy.signal import butter, filtfilt, savgol_filter, find_peaks

def estimate_frequency(times):
    # Convert to datetime (handles nanoseconds automatically)
    t = pd.to_datetime(times).tolist()

    # Remove duplicate values at the head
    while len(t) > 1 and t[1] == t[0]:
        t.pop(1)

    # Remove duplicate values at the tail
    while len(t) > 1 and t[-2] == t[-1]:
        t.pop(-2)

    if len(t) < 2:
        return None

    duration = (t[-1] - t[0]).total_seconds()

    if duration <= 0:
        return None

    return (len(t) - 1) / duration

def read_log_file():
    # Create a hidden root window
    root = tk.Tk()
    root.withdraw()

    # Open file dialog
    file_path = filedialog.askopenfilename(
        title="Select a CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    # Use the selected file path
    if file_path:
        data_loc = file_path
        print("Selected file:", data_loc)
    else:
        print("No file selected.")
        return None

    df = pd.read_csv(data_loc).reset_index(drop=True)

    # print(df.keys())
    return df

# Moving error estimation
def moving_error_estimation(data, window=10):
    data = np.asarray(data, dtype=float)

    # Reference is 'window' samples ago
    reference = np.concatenate((
        np.full(window, data[0]),
        data[:-window]
    ))

    delta = data - reference
    error_percent = np.abs(delta) / np.maximum(np.abs(reference), 1e-12) * 100

    return error_percent

# Low-pass filter
def butter_lowpass(data, fs, cutoff, order=2):
    nyquist = fs / 2
    b, a = butter(order, cutoff / nyquist, btype='low')
    return filtfilt(b, a, data)

# Peak detection
def detect_peaks(data, fs=10, prominence_ratio=0.2, distance_sec=30):
    """
    Detect peaks and troughs on a periodic signal.

    Parameters
    ----------
    data : array_like
        Input signal.
    fs : float
        Sampling frequency (Hz).
    prominence_ratio : float
        Minimum prominence relative to signal amplitude.
    distance_sec : float
        Minimum distance between peaks (seconds).

    Returns
    -------
    peaks : ndarray
        Peak indices.
    troughs : ndarray
        Trough indices.
    data_smooth : ndarray
        Smoothed signal.
    """

    data = np.asarray(data, dtype=float)

    # Smooth the signal (optional)

    window = int(fs * 5)          # 5-second smoothing window
    if window % 2 == 0:
        window += 1               # Savitzky-Golay requires odd window

    data_smooth = savgol_filter(
        data,
        window_length=window,
        polyorder=2
    )
    # Peak detection parameters
    prominence = (
        np.max(data_smooth) - np.min(data_smooth)
    ) * prominence_ratio

    distance = int(distance_sec * fs)


    # Detect peaks

    peaks, peak_properties = find_peaks(
        data_smooth,
        prominence=prominence,
        distance=distance
    )

    # Detect troughs

    troughs, trough_properties = find_peaks(
        -data_smooth,
        prominence=prominence,
        distance=distance
    )

    return peaks, troughs, data_smooth

# find settling index
def find_settling_index(ec, start_idx, end_idx, settle=0.982, smooth=True, window_length=11, polyorder=2):
    """
    Find the settling index using an optional smoothing filter.

    Parameters
    ----------
    ec : array-like
        Input signal.
    start_idx : int
        Start of the transient.
    end_idx : int
        End of the transient.
    settle : float
        Settling percentage (0.982 = 98.2% settled).
    smooth : bool
        Apply Savitzky-Golay smoothing before detection.
    window_length : int
        Must be odd and >= polyorder + 2.
    polyorder : int
        Polynomial order for Savitzky-Golay filter.

    Returns
    -------
    settling_idx : int
    target : float
    """

    ec = np.asarray(ec)

    # Smooth signal if requested
    if smooth:
        # Ensure valid window length
        window_length = min(window_length, len(ec))
        if window_length % 2 == 0:
            window_length -= 1
        window_length = max(window_length, polyorder + 2)
        if window_length % 2 == 0:
            window_length += 1

        ec_filtered = savgol_filter(ec, window_length, polyorder)
    else:
        ec_filtered = ec

    ec0 = ec_filtered[start_idx]
    ecf = ec_filtered[end_idx]

    # Target value corresponding to settle %
    target = ecf + (ec0 - ecf) * (1 - settle)

    segment = ec_filtered[start_idx:end_idx + 1]

    # Find ALL samples that satisfy the criterion
    indices = np.where(segment <= target)[0]

    if len(indices) == 0:
        return None, target

    # Return the first one
    idx_local = indices[0]

    return start_idx + idx_local, target