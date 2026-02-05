import polars as pl


def main():
    df = pl.read_parquet("src/data/gameweek_history.parquet")
    print("Columns:", df.columns)
    print("Shape:", df.shape)
    print("\nFirst row (as dict):")
    row = df.head(1).to_dicts()[0]
    for k, v in row.items():
        print(f"  {k}: {v}")
    print("\nData types:")
    for col, dtype in zip(df.columns, df.dtypes):
        print(f"  {col}: {dtype}")


if __name__ == "__main__":
    main()
