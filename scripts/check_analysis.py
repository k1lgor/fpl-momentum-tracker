import polars as pl

df = pl.read_parquet("src/data/momentum_analysis.parquet")
print("Rows:", df.shape[0])
print("Columns:", df.columns)
print("\nSample rows:")
print(
    df.select(
        [
            "web_name",
            "position",
            "window_size",
            "rolling_xg",
            "rolling_actual",
            "xg_diff",
            "momentum_trend",
            "signal",
        ]
    ).head(5)
)
print("\nSignal counts:")
print(df.group_by("signal").agg(pl.count()).sort("signal"))
print("\nCheck for NaN/Inf:")
for col in df.columns:
    if df[col].dtype in (pl.Float64, pl.Float32):
        nulls = df[col].is_nan().sum()
        infs = df[col].is_infinite().sum()
        if nulls > 0 or infs > 0:
            print(f"{col}: nulls={nulls}, infs={infs}")
