import os
from typing import Tuple
import pandas as pd
import matplotlib.pyplot as plt


def merge_on_time(weather_df: pd.DataFrame, radiation_df: pd.DataFrame) -> pd.DataFrame:
	if "time" not in weather_df.columns or "time" not in radiation_df.columns:
		return pd.DataFrame()
	df = pd.merge(weather_df, radiation_df, on="time", how="outer")
	# Sort by time treating as HH:MM:SS strings
	df["_sort"] = pd.to_datetime(df["time"], errors="coerce").dt.hour * 60 + pd.to_datetime(df["time"], errors="coerce").dt.minute
	df = df.sort_values("_sort").drop(columns=["_sort"])
	return df


def plot_weather_radiation(df: pd.DataFrame, outputs_dir: str = "outputs") -> str:
	os.makedirs(outputs_dir, exist_ok=True)
	fig, ax1 = plt.subplots(figsize=(12, 6))

	x = df["time"]
	# Primary axis: Temperature (if present)
	if "temperature_c" in df.columns:
		ax1.plot(x, df["temperature_c"], color="#d62728", label="Temperature (°C)", linewidth=2)
		ax1.set_ylabel("Temperature (°C)", color="#d62728")
		ax1.tick_params(axis='y', labelcolor="#d62728")
	elif "relative_humidity_pct" in df.columns:
		ax1.plot(x, df["relative_humidity_pct"], color="#1f77b4", label="Relative Humidity (%)", linewidth=2)
		ax1.set_ylabel("Relative Humidity (%)", color="#1f77b4")
		ax1.tick_params(axis='y', labelcolor="#1f77b4")

	# Secondary axis: Radiation
	ax2 = ax1.twinx()
	if "radiation_usv_per_h" in df.columns:
		ax2.plot(x, df["radiation_usv_per_h"], color="#2ca02c", label="Radiation (μSv/h)", linewidth=2)
		ax2.set_ylabel("Radiation (μSv/h)", color="#2ca02c")
		ax2.tick_params(axis='y', labelcolor="#2ca02c")

	ax1.set_xlabel("Time")
	ax1.set_title("Yesterday in Hong Kong: Weather and Radiation Level")
	fig.autofmt_xdate(rotation=45)

	# Build a combined legend
	lines_labels = []
	for ax in [ax1, ax2]:
		handles, labels = ax.get_legend_handles_labels()
		lines_labels.extend(list(zip(handles, labels)))
	if lines_labels:
		handles, labels = zip(*lines_labels)
		fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.1, 0.95))

	output_path = os.path.join(outputs_dir, "yesterday_weather_radiation.png")
	plt.tight_layout()
	plt.savefig(output_path, dpi=150)
	plt.close(fig)
	return output_path
