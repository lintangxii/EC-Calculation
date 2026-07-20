import pandas as pd
import csv
from tkinter import Tk, filedialog
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import os
import numpy as np
from function import estimate_frequency, detect_peaks, find_settling_index

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

# Read CSV
save_file = 1  # Set to True if you want to save the output CSV
data_clip = 0  # Set to True if you want to clip the data

# Data clipping parameters
data_skip = 1200
data_range = 420

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

# Peak detection for EC signal
peaks_loadcell1, troughs_loadcell1, _ = detect_peaks(df["LoadCell1"], fs=fs/4, prominence_ratio=0.01, distance_sec=30)

# critical_points_loadcell1 = np.sort(np.concatenate((peaks_loadcell1, troughs_loadcell1)))
troughs = troughs_loadcell1
peaks = peaks_loadcell1


# Find settling points for each trough
settling_criteria = 0.993  # Settle to 99.3% of the peak value
settling_points_indices = []
for i in range(len(troughs) - 1):
    settling_points_index, settling_target = find_settling_index(df["EC"], troughs[i], troughs[i+1], settle = settling_criteria, polyorder=2, window_length=21)
    settling_points_indices.append(settling_points_index)

# Find settling time
settling_times = (np.array(settling_points_indices) - np.array(peaks))/fs
print(f"Settling times (s): {settling_times.round(2)}")
settling_weights = np.array(df["LoadCell1"].iloc[peaks]) - np.array(df["LoadCell1"].iloc[settling_points_indices])
print(f"Settling weights (g): {settling_weights.round(2)}")

# Create figure with secondary axis
fig = make_subplots(specs=[[{"secondary_y": True}]])

# save to CSV
if save_file == True:
    output_df = pd.DataFrame({
        "Time": df["t_datetime"],
        # "EC": df["magnitude"],
        "EC": df["EC"],
        # "EC_Error": df["EC_Error"],
        # "Temperature": df["temperature"],
        # 'Real': df['real'],
        # 'Imaginary': df['imag'],
    })
    # output_df.to_csv("scope.csv", index=False)

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
    "#FF0400", "#0011FF", "#00CC96", "#AB63FA",
    "#FFA15A", "#19D3F3", "#FF6692", "#B6E880",
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
                shape="spline",
            ),
        ),
        secondary_y=(col.lower() in secondary_y)
    )

fig.add_trace(
    go.Scatter(
        x=df["t_datetime"].iloc[troughs],
        y=df["LoadCell1"].iloc[troughs],
        mode="markers",
        name="LoadCell1 Critical Points",
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
        x=df["t_datetime"].iloc[settling_points_indices],
        y=df["LoadCell1"].iloc[settling_points_indices],
        mode="markers",
        name="LoadCell1 Settling Points",
        marker=dict(
            color="Green",
            size=8,
            symbol="x"
        ),
    ),
    secondary_y=True
)

fig.add_trace(
    go.Scatter(
        x=df["t_datetime"].iloc[settling_points_indices],
        y=df["EC"].iloc[settling_points_indices],
        mode="markers",
        name="EC Settling Points",
        marker=dict(
            color="Black",
            size=8,
            symbol="x"
        ),
    ),
    secondary_y=False
)

fig.add_trace(
    go.Scatter(
        x=df["t_datetime"].iloc[peaks],
        y=df["LoadCell1"].iloc[peaks],
        mode="markers",
        name="LoadCell1 Peaks",
        marker=dict(
            color="Red",
            size=8,
            symbol="x"
        ),
    ),
    secondary_y=True
)

fig.update_layout(
    title=os.path.basename(file_path) + f"\nSettling criteria: {settling_criteria*100:.1f}%",
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