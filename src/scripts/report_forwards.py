import polars as pl
from pathlib import Path


def main():
    df = pl.read_parquet("src/data/momentum_analysis.parquet")

    # Filter for Forwards
    fwds = df.filter((pl.col("position") == "FWD") & (pl.col("window_size") == 6))

    # Sort by rolling xG to find high xG players
    # and look for negative xG_diff (underperformance)
    underperformers = fwds.filter(pl.col("xg_diff") < 0).sort(
        "rolling_xg", descending=True
    )

    print("Top Underperforming Forwards (based on last 6 games):")
    print(
        underperformers.select(
            [
                "web_name",
                "team_name",
                "rolling_xg",
                "rolling_actual",
                "xg_diff",
                "xg_per_90",
                "momentum_trend",
            ]
        ).head(10)
    )


if __name__ == "__main__":
    main()
