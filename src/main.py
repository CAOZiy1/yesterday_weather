import os
from .scraper import fetch_html, parse_yesterday, save_csvs
from .visualize import merge_on_time, plot_weather_radiation


def run() -> None:
	print("Fetching HKO yesterday page...")
	html = fetch_html()

	print("Parsing tables...")
	weather_df, radiation_df = parse_yesterday(html)

	if weather_df.empty:
		print("Warning: Could not parse weather table.")
	if radiation_df.empty:
		print("Warning: Could not parse radiation table.")

	print("Saving CSVs...")
	weather_path, radiation_path = save_csvs(weather_df, radiation_df)
	print(f"Saved: {weather_path}\nSaved: {radiation_path}")

	print("Merging and plotting...")
	merged_df = merge_on_time(weather_df, radiation_df)
	os.makedirs("data", exist_ok=True)
	merged_csv = os.path.join("data", "yesterday_merged.csv")
	merged_df.to_csv(merged_csv, index=False)

	chart_path = plot_weather_radiation(merged_df)
	print(f"Saved: {merged_csv}\nSaved: {chart_path}")


if __name__ == "__main__":
	run()
