## Yesterday Weather HK — A Test of Data Visualization

This project fetches and visualizes yesterday's weather and radiation level in Hong Kong from the Hong Kong Observatory page: `https://www.hko.gov.hk/en/wxinfo/pastwx/ryes.htm`.

### Setup (Windows PowerShell)

1. Create and activate a virtual environment
```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
```

2. Install dependencies
```powershell
pip install -r requirements.txt
```

### Run

Generate CSVs and a chart under `data/` and `outputs/`:
```powershell
python -m src.main
```

### Outputs
- `data/yesterday_weather.csv` — parsed weather time series
- `data/yesterday_radiation.csv` — parsed radiation level time series
- `data/yesterday_merged.csv` — merged by time
- `outputs/yesterday_weather_radiation.png` — combined chart

### Notes
- The scraper is resilient to minor page changes by scanning all tables and matching columns like `Time`, `Temperature`, `Humidity`, `Radiation`.
- If the HKO page structure changes significantly, adjust selectors in `src/scraper.py`.
