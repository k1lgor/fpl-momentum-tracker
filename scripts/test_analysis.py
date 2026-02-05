import polars as pl
import sys

sys.stdout.reconfigure(encoding="utf-8")

df = pl.read_parquet("src/data/momentum_analysis.parquet")
print("Columns:", df.columns)
print("Rows:", df.shape[0])
print("\nSignal counts per window:")
counts = (
    df.group_by(["window_size", "signal"])
    .agg(pl.len().alias("count"))
    .sort(["window_size", "signal"])
)
for row in counts.iter_rows(named=True):
    print(f"Window {row['window_size']} {row['signal']}: {row['count']}")
print("\nSample rows with new columns:")
sample = (
    df.filter(pl.col("window_size") == 6)
    .select(
        [
            "web_name",
            "position",
            "xg_diff",
            "xg_diff_per_90",
            "defcon_score",
            "defcon_per_90",
            "games_played_pct",
            "signal",
        ]
    )
    .head(5)
)
for row in sample.iter_rows(named=True):
    # encode web_name to ascii ignoring errors
    name = row["web_name"].encode("ascii", "ignore").decode("ascii")
    print(
        f"{name} ({row['position']}) xGdiff={row['xg_diff']:.2f}, xGdiff/90={row['xg_diff_per_90']:.2f}, DEFCON={row['defcon_score']:.1f}, DEFCON/90={row['defcon_per_90']:.2f}, games%={row['games_played_pct']:.0%}, signal={row['signal']}"
    )
print("\nCheck for NaN/Inf:")
for col in df.columns:
    if df[col].dtype in (pl.Float64, pl.Float32):
        nulls = df[col].is_nan().sum()
        infs = df[col].is_infinite().sum()
        if nulls > 0 or infs > 0:
            print(f"{col}: nulls={nulls}, infs={infs}")
print(
    "\nRange of xg_diff_per_90:", df["xg_diff_per_90"].min(), df["xg_diff_per_90"].max()
)
print("Range of defcon_per_90:", df["defcon_per_90"].min(), df["defcon_per_90"].max())
