import plotly.graph_objects as go
from plotly.subplots import make_subplots
from function import *
from scipy.interpolate import interp1d
import numpy as np
import pandas as pd

frequency = 10

# load data
df1 = read_log_file()
df2 = read_log_file()

# process data 1
df1 = df1.drop_duplicates(subset="Time", keep="last").reset_index(drop=True)
t1 = pd.to_datetime(df1["Time"])
t1_sec = (t1 - t1[0]).dt.total_seconds()

# Date from the first log
base_date = t1.iloc[0].normalize()   # 2026-07-02 00:00:00

# process data 2
fs2 = estimate_frequency(df2["time"].tolist())
start_time = pd.to_timedelta(df2["time"].iloc[0])
df2["time"] = base_date + start_time + pd.to_timedelta(
    np.arange(len(df2)) / fs2,
    unit="s"
)

t2 = df2["time"]
t2_sec = (t2 - t2[0]).dt.total_seconds()


col1 = ["LoadCell0", "LoadCell1"]
df1_interpolated = interp1d(
    x=t1_sec, 
    y=df1[col1].to_numpy(), 
    kind="slinear",
    axis=0,
    fill_value="extrapolate")

col2 = ["magnitude", "temperature"]
df2_interpolated = interp1d(
    x=t2_sec, 
    y=df2[col2].to_numpy(), 
    kind="slinear",
    axis=0,
    fill_value="extrapolate")


t_sync = np.arange(0, t1_sec.iloc[-1], 1/frequency)
t_delta = (t1[0] - t2[0]).total_seconds()
# print(f"Time delta between df1 and df2: {t_delta}")

LoadCell0, LoadCell1 = df1_interpolated(t_sync).T
Magnitude, Temperature = df2_interpolated(t_sync + t_delta).T
Timestamp = t1[0] + pd.to_timedelta(t_sync, unit="s")

print(Timestamp.shape)

# # save to CSV
output_df = pd.DataFrame({
    "Time": Timestamp,
    "EC": Magnitude,
    "Temperature": Temperature,
    'LoadCell0': LoadCell0,
    'LoadCell1': LoadCell1,
})
output_df.to_csv("output.csv", index=False)

fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(go.Scatter(x=Timestamp, y=Magnitude,
                         name="EC", mode="lines",
                         opacity=0.5, line=dict(color="black")),
              secondary_y=False)

fig.add_trace(go.Scatter(x=Timestamp, y=LoadCell0,
                         name="Load Cell 0", mode="lines",
                         line=dict(color="blue")),
              secondary_y=True)

fig.add_trace(go.Scatter(x=Timestamp, y=LoadCell1,
                         name="Load Cell 1", mode="lines",
                         line=dict(color="yellow")),
              secondary_y=True)

# # fig.add_trace(go.Scatter(x=Time, y=LoadCell2,
# #                          name="Load Cell 2", mode="lines",
# #                          line=dict(color="green")),
# #               secondary_y=False)


# # ---- Right Y axis (Temperature) ----
fig.add_trace(go.Scatter(x=Timestamp, y=Temperature,
                         name="Temperature (°C)", mode="lines",
                         opacity=0.5, line=dict(color="red")),
              secondary_y=True)

# Labels and layout
fig.update_layout(title="EC Signal and Load Cell Data",
                  xaxis_title="Time",
                  hovermode="x unified",
                  template="plotly_white")

fig.update_yaxes(title_text="EC", secondary_y=False)
fig.update_yaxes(title_text="Temperature (°C) and Load Cells (g)", secondary_y=True)

fig.show()