# ⚽ FPL xG Momentum Tracker

Identify underperforming gems and overperforming traps in Fantasy Premier League using rolling Expected Goals (xG) analysis and statistical momentum trends.

## 🚀 Overview

This tool analyzes official FPL data to find players whose actual goal output is diverging from their underlying performance. It uses **rolling windows** (4, 6, 10 games) and **linear regression** to identify:

- **💎 Underperformers (BUY)**: Players with high xG but low actual goals (the "unlucky" ones due for regression to the mean).
- **🚀 Rising Stars**: Players whose underlying threat (xG/90) is rapidly improving.
- **⚠️ Sustainability Risks (SELL)**: Players outscoring their xG significantly (the "lucky" ones likely to dry up).

## 🛠️ Tech Stack

- **Python 3.12+**
- **uv**: Ultra-fast Python package installer and resolver.
- **Polars**: High-performance DataFrame library for data processing.
- **Streamlit**: Interactive web UI for visualization.
- **Altair**: Declarative statistical visualization.
- **SciPy**: Linear regression for momentum calculation.
- **pytest**: Testing framework for quality assurance.

## 🏃 Getting Started

### 1. Installation

Ensure you have [uv](https://github.com/astral-sh/uv) installed.

```bash
# Install dependencies
uv sync

# Install development dependencies (includes pytest)
uv sync --extra dev
```

### 2. Task Execution (Just)

If you have [just](https://github.com/casey/just) installed, you can use shorter commands:

```bash
just setup       # Install dependencies
just install-dev # Install dev dependencies
just update      # Refresh data and run analysis
just ui          # Launch the dashboard
just test        # Run test suite
```

### 3. Manual Execution

**Fetch fresh data from the FPL API:**

```bash
uv run src/scripts/fetch_data.py
```

**Run the momentum analysis engine:**

```bash
uv run src/scripts/analyze_momentum.py
```

**Launch the Dashboard:**

```bash
uv run streamlit run src/app.py
```

## 📁 Project Structure

```
fpl-momentum-tracker/
├── src/
│   ├── app.py                      # Streamlit dashboard
│   ├── data/                       # Generated data files (gitignored)
│   └── scripts/
│       ├── fetch_data.py           # FPL API data fetcher
│       ├── analyze_momentum.py     # xG momentum analysis engine
│       └── report_forwards.py      # Specific forward analysis
├── tests/                          # Test suite
│   ├── conftest.py                 # Pytest configuration
│   ├── test_fetch_data.py          # Data fetcher tests
│   └── test_analyze_momentum.py    # Analysis engine tests
├── scripts/                        # Utility scripts for inspection
├── Justfile                        # Task runner commands
├── pyproject.toml                  # Project dependencies
└── README.md                       # This file
```

## 📖 Key Metrics Explained

### xG Diff (Expected Goals Difference)

- **Negative (-1.5)**: Underperforming. The player is getting chances but not scoring. Regression to the mean suggests they are "due".
- **Positive (+1.5)**: Overperforming. The player is scoring at an unsustainable rate compared to the quality of their chances.

### Momentum Trend

- **↗️ Positive (>0.0)**: Underlying numbers are improving. The player is finding better chances each game.
- **↘️ Negative (<0.0)**: Underlying numbers are declining. The player's threat is fading.

### DEFCON Score

A composite defensive metric combining:

- Tackles
- Recoveries (weighted at 0.25x)
- Clearances, Blocks, and Interceptions (CBI)

Higher DEFCON scores indicate more defensive contribution.

## 🧪 Testing

Run the test suite to ensure everything works correctly:

```bash
# Run all tests
just test

# Or manually with pytest
uv run pytest tests/ -v

# Run tests in watch mode (stops on first failure)
just test-watch
```

## 🔧 Troubleshooting

### "Analysis file not found" error

Run the data pipeline first:

```bash
just update
```

### API connection errors

The FPL API occasionally experiences downtime. Wait a few minutes and try again. The script includes automatic error handling and will inform you of connection issues.

### Empty data files

If you're running this very early in the season (before gameweek 1), there may be no historical data available. The scripts will handle this gracefully.

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Report bugs**: Open an issue with details about the problem
2. **Suggest features**: Share ideas for new analysis metrics or visualizations
3. **Submit PRs**: Fork the repo, make your changes, and submit a pull request

### Development Workflow

1. Install dev dependencies: `just install-dev`
2. Make your changes
3. Run tests: `just test`
4. Ensure code quality (no lint errors)
5. Submit a PR with a clear description

## 📊 Data Sources

All data is fetched from the official [Fantasy Premier League API](https://fantasy.premierleague.com/api/):

- Bootstrap static data (players, teams, gameweeks)
- Player gameweek history (performance metrics)

## 📝 License

This project is for educational and personal use. All FPL data belongs to the Premier League.

---

Built with ⚽ for FPL Managers by data-driven enthusiasts.
