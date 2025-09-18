import os
from typing import Optional, Tuple
import requests
from bs4 import BeautifulSoup
import pandas as pd

HKO_YESTERDAY_URL = "https://www.hko.gov.hk/en/wxinfo/pastwx/ryes.htm"


def fetch_html(url: str = HKO_YESTERDAY_URL, timeout_seconds: int = 20) -> str:
	headers = {
		"User-Agent": (
			"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
			"(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
		)
	}
	response = requests.get(url, headers=headers, timeout=timeout_seconds)
	response.raise_for_status()
	response.encoding = response.apparent_encoding or response.encoding
	return response.text


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
	df = df.copy()
	df.columns = [str(c).strip().lower() for c in df.columns]
	return df


def _find_time_column(df: pd.DataFrame) -> Optional[str]:
	for col in df.columns:
		name = str(col).lower()
		if "time" == name or name.startswith("time") or "hour" in name:
			return col
	return None


def _coerce_time(df: pd.DataFrame, time_col: str) -> pd.DataFrame:
	df = df.copy()
	# Keep original for reference
	df["time_raw"] = df[time_col].astype(str)
	# Try multiple common formats seen on HKO tables
	for fmt in ["%H:%M", "%H%M", "%H:%M:%S", "%I:%M %p", "%H"]:
		try:
			parsed = pd.to_datetime(df[time_col].astype(str).str.strip(), format=fmt, errors="raise").dt.time
			df["time"] = parsed.astype(str)
			return df
		except Exception:
			continue
	# Fallback to pandas best-effort
	df["time"] = pd.to_datetime(df[time_col].astype(str).str.strip(), errors="coerce").dt.time.astype(str)
	return df


def _select_weather_columns(df: pd.DataFrame) -> pd.DataFrame:
	df = _normalize_columns(df)
	time_col = _find_time_column(df)
	if not time_col:
		return pd.DataFrame()
	df = _coerce_time(df, time_col)

	# Candidate columns
	temp_cols = [c for c in df.columns if any(k in c for k in ["temp", "temperature", "t(\u00b0c)"])]
	rh_cols = [c for c in df.columns if any(k in c for k in ["rh", "humidity", "rel hum", "relative humidity"])]
	rain_cols = [c for c in df.columns if "rain" in c or "rainfall" in c]

	cols = ["time"] + temp_cols[:1] + rh_cols[:1] + rain_cols[:1]
	cols = [c for c in cols if c in df.columns]
	if len(cols) <= 1:
		return pd.DataFrame()

	out = df[cols].copy()
	out.rename(columns={
		temp_cols[0] if temp_cols else None: "temperature_c",
		rh_cols[0] if rh_cols else None: "relative_humidity_pct",
		rain_cols[0] if rain_cols else None: "rainfall_mm",
	}, inplace=True)

	# Numeric coercions
	for c in ["temperature_c", "relative_humidity_pct", "rainfall_mm"]:
		if c in out.columns:
			out[c] = pd.to_numeric(out[c].astype(str).str.extract(r"([-+]?\d*\.?\d+)")[0], errors="coerce")

	return out


def _select_radiation_columns(df: pd.DataFrame) -> pd.DataFrame:
	df = _normalize_columns(df)
	time_col = _find_time_column(df)
	if not time_col:
		return pd.DataFrame()
	df = _coerce_time(df, time_col)

	rad_cols = [c for c in df.columns if any(k in c for k in ["radiation", "rad level", "\u00b5sv", "usv", "nsv"]) ]
	if not rad_cols:
		# also check unit-like columns
		rad_cols = [c for c in df.columns if "sv" in c]
	cols = ["time"] + rad_cols[:1]
	cols = [c for c in cols if c in df.columns]
	if len(cols) <= 1:
		return pd.DataFrame()

	out = df[cols].copy()
	out.rename(columns={cols[1]: "radiation"}, inplace=True)

	# Try to detect scale from header text
	header_text = " ".join(df.columns)
	scale = 1.0
	if any(u in header_text for u in ["\u00b5sv", "μsv", "micro-sievert", "micro sievert"]):
		scale = 1.0  # already micro-sievert per hour
	elif "nsv" in header_text:
		scale = 0.001  # nano to micro

	out["radiation"] = pd.to_numeric(out["radiation"].astype(str).str.extract(r"([-+]?\d*\.?\d+)")[0], errors="coerce")
	out["radiation_usv_per_h"] = out["radiation"] * scale
	out.drop(columns=["radiation"], inplace=True)
	return out


def parse_yesterday(html: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
	soup = BeautifulSoup(html, "lxml")

	# Use pandas to read all tables for robustness
	all_tables = pd.read_html(html, flavor="lxml")

	weather_df = pd.DataFrame()
	radiation_df = pd.DataFrame()

	for table in all_tables:
		if weather_df.empty:
			candidate_weather = _select_weather_columns(table)
			if not candidate_weather.empty:
				weather_df = candidate_weather
		if radiation_df.empty:
			candidate_rad = _select_radiation_columns(table)
			if not candidate_rad.empty:
				radiation_df = candidate_rad
		if not weather_df.empty and not radiation_df.empty:
			break

	# Fallbacks: try to locate via headings context if necessary
	if weather_df.empty or radiation_df.empty:
		# Look for tables near headings
		for header in soup.find_all(["h2", "h3", "h4", "strong", "b"]):
			heading = header.get_text(" ", strip=True).lower()
			next_table = header.find_next("table")
			if not next_table:
				continue
			try:
				df = pd.read_html(str(next_table))[0]
			except Exception:
				continue
			if weather_df.empty and any(k in heading for k in ["weather", "yesterday", "temperature", "humidity", "rain"]):
				candidate_weather = _select_weather_columns(df)
				if not candidate_weather.empty:
					weather_df = candidate_weather
			if radiation_df.empty and any(k in heading for k in ["radiation", "rad", "sievert"]):
				candidate_rad = _select_radiation_columns(df)
				if not candidate_rad.empty:
					radiation_df = candidate_rad
			if not weather_df.empty and not radiation_df.empty:
				break

	return weather_df, radiation_df


def save_csvs(weather_df: pd.DataFrame, radiation_df: pd.DataFrame, data_dir: str = "data") -> Tuple[str, str]:
	os.makedirs(data_dir, exist_ok=True)
	weather_path = os.path.join(data_dir, "yesterday_weather.csv")
	radiation_path = os.path.join(data_dir, "yesterday_radiation.csv")
	weather_df.to_csv(weather_path, index=False)
	radiation_df.to_csv(radiation_path, index=False)
	return weather_path, radiation_path
