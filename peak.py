import pandas as pd
import csv
from tkinter import Tk, filedialog
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import os
import numpy as np
from function import estimate_frequency, detect_peaks
from time import strftime

# Peak filter
def peak_filter(data, threshold=0.98):
    """
    Filters out peaks in the data that are below a certain threshold.

    Parameters:
    - data: A 1D numpy array or list of data points.
    - threshold: A float value representing the minimum peak height to keep.

    Returns:
    - average_peak: A float value representing the average height of the peaks above the threshold.
    """
    # Convert to numpy array if it's a list
    data = np.array(data)

    # Find max value in the data
    max_value = np.max(data)

    # Compute range based on the threshold
    range_value = max_value * threshold

    # Filter out peaks below the threshold
    filtered_peaks = data[data >= range_value]

    # find the average of the filtered peaks
    average_peak = np.mean(filtered_peaks)
    
    return average_peak

# Hide Tkinter window
root = Tk()
root.withdraw()

# Select CSV
file_path = filedialog.askopenfilename(
    title="Select CSV File",
    filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
)

if not file_path:
    print("No file selected.")
    exit()

# Parameters
save_file = 0  # Set to True if you want to save the output CSV
data_clip = 0  # Set to True if you want to clip the data
analytical_mode = 1  # Set to True if you want to run in analytical mode

# save file parameters
file_name = f'Output {strftime("%Y-%m-%d_%H-%M-%S")}'  # Name of the output CSV file (without extension)

# Data clipping parameters
data_skip = 775            # Number of data points to skip from the beginning by index
data_range = 100            # Number of data points to include by index

if data_clip == 1:
    df = pd.read_csv(file_path).iloc[data_skip:int(data_skip) + int(data_range)].reset_index(drop=True)
else:
    df = pd.read_csv(file_path)

time_col = df.columns[0]

# Estimate frequency
fs = estimate_frequency(df[time_col])
print(f"Estimated frequency: {fs:.2f} Hz")

# Create elapsed time in seconds (matches df length exactly)
df["t_sec"] = np.arange(len(df)) / fs

# Convert to datetime relative to first timestamp in the sliced data
df["t_datetime"] = pd.to_datetime(df["t_sec"], unit="s", origin=df[time_col].iloc[0])

if analytical_mode == 1:
    # Peak detection for EC signal
    peaks_loadcell1, troughs_loadcell1, _ = detect_peaks(df["LoadCell1"], fs=1, prominence_ratio=0.025, distance_sec=20)

    # critical_points_loadcell1 = np.sort(np.concatenate((peaks_loadcell1, troughs_loadcell1)))
    troughs = troughs_loadcell1
    peaks = peaks_loadcell1

    # create an array to store the filtered peak values
    filtered_peaks = np.zeros_like(df["EC"])

    for i in range(len(troughs) - 1):
        # slice the data between the current peak and the next trough
        sliced_data_EC = df["EC"].iloc[peaks[i]:troughs[i + 1]]
        filtered_peak = peak_filter(sliced_data_EC)
        filtered_peaks[peaks[i]:troughs[i + 1]] = filtered_peak

    df["Filtered_EC_Peaks"] = filtered_peaks

    # Find settling points for each trough    
    # settling_points_indices = []
    # for i in range(len(troughs) - 1):
    #     settling_points_index, settling_target = find_settling_index(df["EC"], troughs[i], troughs[i+1], settle = settling_criteria, polyorder=savgol_polyorder, window_length=savgol_window_length)
    #     settling_points_indices.append(settling_points_index)

    # Find settling time
    # settling_times = (np.array(settling_points_indices) - np.array(peaks))/fs
    # print(f"Settling times (s): {settling_times.round(2)}")
    # settling_weights = np.array(df["LoadCell1"].iloc[peaks]) - np.array(df["LoadCell1"].iloc[settling_points_indices])
    # print(f"Settling weights (g): {settling_weights.round(2)}")

# Create figure with secondary axis
fig = make_subplots(specs=[[{"secondary_y": True}]])

# save to CSV
if save_file == True:
    output_df = pd.DataFrame({
        "Time": df["t_datetime"],                   # you can also add other columns as needed. example: "{Column Name}": df["{Column Name}"],
        "EC": df["magnitude"],
        # "EC": df["EC"],
        # "EC_Error": df["EC_Error"],
        "Temperature": df["temperature"],
        # 'Real': df['real'],
        # 'Imaginary': df['imag'],
    })
    output_df.to_csv(f"{file_name}.csv", index=False)

    # data_attributes = [
    #     df["t_datetime"].iloc[troughs],
    #     settling_points_indices,
    # ]
    
    # with open("output_attributes.csv", "w", newline="") as f:
    #     writer = csv.writer(f)
    #     for i in data_attributes:
    #         writer.writerow(i)

# Define colors for the traces
colors = [
    "#FF0400", 
    "#0011FF", 
    "#00CC96", 
    "#AB63FA",
    "#FFA15A", 
    "#19D3F3", 
    "#0B106A", 
    "#B6E880",
    "#F319B5"
]


# Add traces for each column in the DataFrame
for i, col in enumerate(df.columns[1:]):
    if col == "t_sec" or col == "t_datetime":
        continue  # Skip time columns

    # Skip non-numeric columns
    if not pd.api.types.is_numeric_dtype(df[col]):
        continue
    

    # Secondary axis
    secondary_y = {
    'temperature',
    'loadcell0',
    'loadcell1',
    'ec_error'
    }

    fig.add_trace(
        go.Scatter(
            x=df["t_datetime"],
            y=df[col],
            mode="lines",
            name=col,
            line=dict(
                color=colors[i % len(colors)],
                width=2,
                shape="linear"  # Use "linear" for straight lines, "spline" for smooth curves
            ),
        ),
        secondary_y=(col.lower() in secondary_y)
    )


if analytical_mode == 1:
    fig.add_trace(
    go.Scatter(
        x=df["t_datetime"].iloc[troughs],
        y=df["LoadCell1"].iloc[troughs],
        mode="markers",
        name="Peak to peak reference",
        marker=dict(
            color="Blue",
            size=8,
            symbol="x"
        ),
    ),
    secondary_y=True
)

    fig.add_trace(
        go.Scatter(
            x=df["t_datetime"].iloc[peaks],
            y=df["LoadCell1"].iloc[peaks],
            mode="markers",
            name="Concentration starting point",
            marker=dict(
                color="#FF00EA",
                size=8,
                symbol="x"
            ),
        ),
        secondary_y=True
    )

fig.update_layout(
    title=os.path.basename(file_path),
    template="plotly_white",
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0
    )
)

fig.update_xaxes(title_text=df.columns[0])
fig.update_yaxes(title_text="Value", secondary_y=False)
fig.update_yaxes(title_text="Temperature (°C)", secondary_y=True)

fig.show()