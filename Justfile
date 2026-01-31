# FPL Momentum Tracker - Task Runner

# Default task: list all commands
default:
    @just --list

# Initialize project and install dependencies
setup:
    uv sync

# Fetch fresh data from the FPL API
fetch:
    uv run src/scripts/fetch_data.py

# Run the momentum analysis engine
analyze:
    uv run src/scripts/analyze_momentum.py

# Complete data refresh pipeline (Fetch + Analyze)
update: fetch analyze

# Launch the interactive Streamlit dashboard
ui:
    uv run streamlit run src/app.py

# Run the specific underperforming forwards report
report-fwds:
    uv run src/scripts/report_forwards.py

# Clean up data cache
clean:
    rm -rf src/data/*.parquet
