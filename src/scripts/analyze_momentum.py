import polars as pl
from pathlib import Path
import numpy as np
from scipy import stats

DATA_DIR = Path("src/data")
PLAYERS_FILE = DATA_DIR / "players.parquet"
HISTORY_FILE = DATA_DIR / "gameweek_history.parquet"
OUTPUT_FILE = DATA_DIR / "momentum_analysis.parquet"


def calculate_momentum_score(y):
    """
    Calculate a Reliability-Weighted Slope for time series data.

    Returns: Slope * R^2.
    This metric identifies trends that are both STEEP (improving) and STEADY (reliable).
    Regular slope can be misleading with outliers; R^2 ensures the trend is consistent.
    """
    if len(y) < 3:  # Need at least 3 points for a meaningful R-squared
        return 0.0

    valid_pairs = [
        (i, float(v)) for i, v in enumerate(y) if v is not None and not np.isnan(v)
    ]

    if len(valid_pairs) < 3:
        return 0.0

    try:
        x_clean = np.array([p[0] for p in valid_pairs])
        y_clean = np.array([p[1] for p in valid_pairs])

        # Linear regression returns: slope, intercept, r_value, p_value, std_err
        slope, _, r_value, _, _ = stats.linregress(x_clean, y_clean)

        # Handle cases where variance is zero or calculation is invalid (results in NaN)
        if np.isnan(slope) or np.isnan(r_value):
            return 0.0

        # R-Squared (Statistical Certainty)
        r_squared = r_value**2

        # Weighted score: Penalizes high variance (low R^2)
        return float(slope * r_squared)
    except Exception:
        return 0.0


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

    # Cast metrics to Float64 safely (handle string decimals)
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
    cast_exprs = []
    for col in metrics_to_cast:
        if df.schema[col] == pl.String:
            cast_exprs.append(pl.col(col).str.replace(",", ".").cast(pl.Float64))
        else:
            cast_exprs.append(pl.col(col).cast(pl.Float64))
    df = df.with_columns(cast_exprs)

    # Add per-game xGI per 90 and minutes indicator
    # xGI (Expected Goal Involvement) is more holistic for MIDs and FWDs
    df = df.with_columns(
        pl.when(pl.col("minutes") > 0)
        .then(pl.col("expected_goal_involvements") * 90 / pl.col("minutes"))
        .otherwise(0)
        .alias("xgi_per_90_per_game")
    )
    df = df.with_columns((pl.col("minutes") > 0).alias("minutes_gt_zero"))

    # Sort by player and gameweek/round (ensure chronological)
    df = df.sort(["player_id", "round"])

    # Define windows
    windows = [4, 6, 10]
    results = []

    for w in windows:
        print(f"Processing window size: {w}")

        # Calculate rolling metrics - Only consider games where player played > 0 minutes
        windowed_df = df.group_by("player_id").agg(
            [
                pl.col("web_name").first(),
                pl.col("position").first(),
                pl.col("team_name").first(),
                pl.col("now_cost").first(),
                # Filter by minutes > 0 before summing to avoid data leakage
                pl.col("expected_goals").filter(pl.col("minutes") > 0).tail(w).sum().alias("rolling_xg"),
                pl.col("goals_scored").filter(pl.col("minutes") > 0).tail(w).sum().alias("rolling_actual"),
                pl.col("expected_goals_conceded").filter(pl.col("minutes") > 0).tail(w).sum().alias("rolling_xgc"),
                pl.col("clean_sheets").filter(pl.col("minutes") > 0).tail(w).sum().alias("rolling_cs"),
                pl.col("goals_conceded").filter(pl.col("minutes") > 0).tail(w).sum().alias("rolling_gc"),
                pl.col("tackles").filter(pl.col("minutes") > 0).tail(w).sum().alias("rolling_tackles"),
                pl.col("recoveries").filter(pl.col("minutes") > 0).tail(w).sum().alias("rolling_recoveries"),
                pl.col("clearances_blocks_interceptions")
                .filter(pl.col("minutes") > 0)
                .tail(w)
                .sum()
                .alias("rolling_cbi"),
                pl.col("saves").filter(pl.col("minutes") > 0).tail(w).sum().alias("rolling_saves"),
                pl.col("minutes").filter(pl.col("minutes") > 0).tail(w).sum().alias("rolling_minutes"),
                pl.col("expected_goals").tail(w).alias("xg_sequence"),
                pl.col("xgi_per_90_per_game").tail(w).alias("xgi_per_90_sequence"),
                # Count of games with minutes > 0 in window
                pl.col("minutes_gt_zero").tail(w).sum().alias("games_played_in_window"),
            ]
        )

        # Add xG diff and DEFCON metrics
        windowed_df = windowed_df.with_columns(
            [
                (pl.col("rolling_actual") - pl.col("rolling_xg")).alias("xg_diff"),
                # xG Diff per 90 minutes (with zero-division guard)
                pl.when(pl.col("rolling_minutes") > 0)
                .then(
                    (pl.col("rolling_actual") - pl.col("rolling_xg"))
                    / (pl.col("rolling_minutes") / 90)
                )
                .otherwise(0)
                .alias("xg_diff_per_90"),
                # xG per 90 minutes (with zero-division guard)
                pl.when(pl.col("rolling_minutes") > 0)
                .then(pl.col("rolling_xg") / pl.col("rolling_minutes") * 90)
                .otherwise(0)
                .alias("xg_per_90"),
                # Adjusted minutes percentage based on actual games played
                (pl.col("games_played_in_window") / w).alias("games_played_pct"),
                (pl.col("rolling_minutes") / (w * 90)).alias("minutes_pct"),
                # DEFCON Score: Tackles (1.0x) + Recoveries (0.25x) + CBI (1.0x)
                # Rationale: Tackles and CBI are direct defensive actions
                # Recoveries are weighted lower as they're less impactful
                (
                    pl.col("rolling_tackles")
                    + (pl.col("rolling_recoveries") / 4.0)
                    + pl.col("rolling_cbi")
                ).alias("defcon_score"),
            ]
        )
        # DEFCON per 90 (normalized by minutes, with zero-division guard)
        # Reuse the defcon_score and normalize by minutes
        windowed_df = windowed_df.with_columns(
            pl.when(pl.col("rolling_minutes") > 0)
            .then(pl.col("defcon_score") / pl.col("rolling_minutes") * 90)
            .otherwise(0)
            .alias("defcon_per_90")
        )

        # Calculate momentum score (Reliability-Weighted Slope) on xGI per 90 sequence
        # This identifies players whose threat is both improving and consistent.
        windowed_df = windowed_df.with_columns(
            pl.col("xgi_per_90_sequence")
            .map_elements(calculate_momentum_score, return_dtype=pl.Float64)
            .alias("momentum_score")
        )

        # Generate improved signals with clear decision rules
        #
        # BUY Signal:
        #   - Underperforming: xG Diff < -0.5 (getting chances but not scoring)
        #   - Improving & Steady: momentum_score > 0.005 (Refined threshold for weighted slope)
        #   - Regular starter: Games played > 50% (reliable minutes)
        #
        # SELL Signal:
        #   - Overperforming with decline: xG Diff > 0.8 AND momentum_score < -0.005
        #     (Scoring unsustainably with declining underlying numbers)
        #   - OR rotation risk with overperformance: Games played < 30% AND xG Diff > 1.0 
        #     (Very low minutes but very high overperformance - likely to regress or lose place)
        #
        # HOLD: Everything else
        windowed_df = windowed_df.with_columns(
            pl.when(
                (pl.col("xg_diff") < -0.5)
                & (pl.col("momentum_score") > 0.005)
                & (pl.col("games_played_pct") > 0.5)
            )
            .then(pl.lit("BUY"))
            .when(
                # Overperforming with declining underlying trend
                ((pl.col("xg_diff") > 0.8) & (pl.col("momentum_score") < -0.005))
                # OR severe rotation risk with extreme overperformance
                # (tighter thresholds: <30% games and >1.0 xG diff to avoid false positives)
                | ((pl.col("games_played_pct") < 0.3) & (pl.col("xg_diff") > 1.0))
            )
            .then(pl.lit("SELL"))
            .otherwise(pl.lit("HOLD"))
            .alias("signal")
        )

        windowed_df = windowed_df.with_columns(pl.lit(w).alias("window_size"))
        results.append(windowed_df.drop(["xg_sequence", "xgi_per_90_sequence"]))

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
        buys.select(["web_name", "position", "team_name", "xg_diff", "momentum_score"])
    )


if __name__ == "__main__":
    main()
