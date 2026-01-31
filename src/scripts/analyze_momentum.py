import polars as pl
from pathlib import Path
import numpy as np
from scipy import stats

DATA_DIR = Path("src/data")
PLAYERS_FILE = DATA_DIR / "players.parquet"
HISTORY_FILE = DATA_DIR / "gameweek_history.parquet"
OUTPUT_FILE = DATA_DIR / "momentum_analysis.parquet"


def calculate_slope(y):
    if len(y) < 2:
        return 0.0
    x = np.arange(len(y))
    slope, _, _, _, _ = stats.linregress(x, y)
    return slope


# Registering a custom function for Polars is tricky for complex things,
# but we can use map_batches for small arrays if needed.
# Since we want rolling slope, we can use a window function.


def main():
    if not PLAYERS_FILE.exists() or not HISTORY_FILE.exists():
        print("Data files not found. Run fetch_data.py first.")
        return

    players_df = pl.read_parquet(PLAYERS_FILE)
    history_df = pl.read_parquet(HISTORY_FILE)

    # Join players and history
    df = history_df.join(players_df, left_on="player_id", right_on="id")

    # Cast metrics to Float64
    metrics_to_cast = [
        "expected_goals",
        "expected_assists",
        "expected_goal_involvements",
        "expected_goals_conceded",
        "influence",
        "creativity",
        "threat",
        "ict_index",
    ]
    df = df.with_columns([pl.col(col).cast(pl.Float64) for col in metrics_to_cast])

    # Sort by player and gameweek/round (ensure chronological)
    df = df.sort(["player_id", "round"])

    # Define windows
    windows = [4, 6, 10]
    results = []

    for w in windows:
        print(f"Processing window size: {w}")

        # Calculate rolling metrics
        windowed_df = df.group_by("player_id").agg(
            [
                pl.col("web_name").first(),
                pl.col("position").first(),
                pl.col("team_name").first(),
                pl.col("now_cost").first(),
                pl.col("expected_goals").tail(w).sum().alias("rolling_xg"),
                pl.col("goals_scored").tail(w).sum().alias("rolling_actual"),
                pl.col("minutes").tail(w).sum().alias("rolling_minutes"),
                pl.col("expected_goals").tail(w).alias("xg_sequence"),
            ]
        )

        # Add xG diff
        windowed_df = windowed_df.with_columns(
            [
                (pl.col("rolling_actual") - pl.col("rolling_xg")).alias("xg_diff"),
                (pl.col("rolling_xg") / pl.col("rolling_minutes") * 90)
                .fill_nan(0)
                .alias("xg_per_90"),
                (pl.col("rolling_minutes") / (w * 90)).alias("minutes_pct"),
            ]
        )

        # Calculate momentum trend (slope)
        # We'll use a python function for the slope calculation on the sequence
        windowed_df = windowed_df.with_columns(
            pl.col("xg_sequence")
            .map_elements(calculate_slope, return_dtype=pl.Float64)
            .alias("momentum_trend")
        )

        # Generate signals
        # BUY: xG_diff < -0.5 (underperforming), momentum_trend > 0.1 (improving), minutes_pct > 60%
        # SELL: xG_diff > 1.0 (overperforming), momentum_trend < -0.1 (declining)
        windowed_df = windowed_df.with_columns(
            pl.when(
                (pl.col("xg_diff") < -0.5)
                & (pl.col("momentum_trend") > 0.05)
                & (pl.col("minutes_pct") > 0.6)
            )
            .then(pl.lit("BUY"))
            .when((pl.col("xg_diff") > 1.0) & (pl.col("momentum_trend") < -0.05))
            .then(pl.lit("SELL"))
            .otherwise(pl.lit("HOLD"))
            .alias("signal")
        )

        windowed_df = windowed_df.with_columns(pl.lit(w).alias("window_size"))
        results.append(windowed_df.drop("xg_sequence"))

    # Combine results
    final_df = pl.concat(results)

    # Save to Parquet
    final_df.write_parquet(OUTPUT_FILE)
    print(f"Analysis saved to {OUTPUT_FILE}")

    # Display top 5 BUY for window 6
    print("\nTop 5 BUY Recommendations (Window 6):")
    buys = (
        final_df.filter((pl.col("window_size") == 6) & (pl.col("signal") == "BUY"))
        .sort("xg_diff")
        .head(5)
    )
    print(
        buys.select(["web_name", "position", "team_name", "xg_diff", "momentum_trend"])
    )


if __name__ == "__main__":
    main()
