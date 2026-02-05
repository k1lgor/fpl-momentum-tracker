import polars as pl


def main():
    """
    Generate a report of underperforming forwards based on xG momentum analysis.

    Focuses on forwards with:
    - BUY signal (underperforming with improving momentum)
    - Minimum xG threshold (at least 1.0 xG in the window)
    """
    df = pl.read_parquet("src/data/momentum_analysis.parquet")

    # Filter for Forwards with 6-game window
    fwds = df.filter((pl.col("position") == "FWD") & (pl.col("window_size") == 6))

    # Focus on forwards with BUY signal and meaningful xG levels
    # BUY signal already includes:
    #   - Underperformance (xg_diff < -0.5)
    #   - Improving momentum (trend > 0.02)
    #   - Regular minutes (>50% games played)
    buy_candidates = fwds.filter(
        (pl.col("signal") == "BUY")
        & (pl.col("rolling_xg") >= 1.0)  # At least 1.0 xG in window
    ).sort("xg_diff")  # Most underperforming first

    print("🎯 Top BUY Forwards (Underperforming with Improving Momentum):")
    print("=" * 80)

    if buy_candidates.is_empty():
        print("No forwards currently meet the BUY criteria.")
    else:
        print(
            buy_candidates.select(
                [
                    "web_name",
                    "team_name",
                    "rolling_xg",
                    "rolling_actual",
                    "xg_diff",
                    "xg_per_90",
                    "momentum_score",
                    "games_played_pct",
                ]
            ).head(10)
        )
        print(f"\nTotal BUY candidates: {len(buy_candidates)}")


if __name__ == "__main__":
    main()
