# ⚽ FPL xG Momentum Tracker

Identify underperforming gems and overperforming traps in Fantasy Premier League using rolling Expected Goals (xG) analysis and statistical momentum trends.

## 🚀 Overview

This tool analyzes official FPL data to find players whose actual goal output is diverging from their underlying underlying performance. It uses **rolling windows** (4, 6, 10 games) and **linear regression** to identify:

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

## 🏃 Getting Started

### 1. Installation

Ensure you have [uv](https://github.com/astral-sh/uv) installed.

```bash
uv sync
```

### 2. Task Execution (Just)

If you have [just](https://github.com/casey/just) installed, you can use shorter commands:

```bash
just setup    # Install dependencies
just update   # Refresh data and run analysis
just ui       # Launch the dashboard
```

### 3. Manual Execution

Fetch fresh data from the FPL API:

```bash
uv run src/scripts/fetch_data.py
```

Run the momentum analysis engine:

```bash
uv run src/scripts/analyze_momentum.py
```

### 3. Launch the Dashboard

```bash
uv run streamlit run src/app.py
```

## 📖 Key Metrics Explained

### xG Diff (Expected Goals Difference)

- **Negative (-1.5)**: Underperforming. The player is getting chances but not scoring. Regression to the mean suggests they are "due".
- **Positive (+1.5)**: Overperforming. The player is scoring at an unsustainable rate compared to the quality of their chances.

### Momentum Trend

- **↗️ Positive (>0.0)**: Underlying numbers are improving. The player is finding better chances each game.
- **↘️ Negative (<0.0)**: Underlying numbers are declining. The player's threat is fading.

---

Built with ⚽ for FPL Managers.
