import streamlit as st
import polars as pl
import altair as alt
from pathlib import Path

# Constants
DATA_DIR = Path("src/data")
ANALYSIS_FILE = DATA_DIR / "momentum_analysis.parquet"

# Page Config
st.set_page_config(page_title="FPL xG Momentum Tracker", page_icon="⚽", layout="wide")

# Custom Styling
st.markdown(
    """
<style>
    .main {
        background-color: #0d1117;
    }
    .stMetric {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22;
    }
    h1, h2, h3 {
        color: #00ff87 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #161b22;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #30363d;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def load_data():
    if not ANALYSIS_FILE.exists():
        st.error("Analysis file not found! Please run the data pipeline first.")
        return None
    return pl.read_parquet(ANALYSIS_FILE)


def main():
    st.title("⚽ FPL xG Momentum Tracker")
    st.markdown(
        "Identify underperforming gems and overperforming traps using rolling xG analysis."
    )

    display_df = load_data()
    if display_df is None:
        return

    # Sidebar Filters
    st.sidebar.header("Filters")

    window_size = st.sidebar.radio("Rolling Window (Games)", [4, 6, 10], index=1)

    positions = st.sidebar.multiselect(
        "Positions", options=["GKP", "DEF", "MID", "FWD"], default=["DEF", "MID", "FWD"]
    )

    signals = st.sidebar.multiselect(
        "Signals", options=["BUY", "HOLD", "SELL"], default=["BUY", "HOLD", "SELL"]
    )

    price_range = st.sidebar.slider(
        "Price Range (£m)",
        min_value=float(display_df["now_cost"].min() / 10),
        max_value=float(display_df["now_cost"].max() / 10),
        value=(4.0, 15.0),
    )

    # Filter Data - Strictly exclude any player with 0 active minutes
    filtered_df = display_df.filter(
        (pl.col("window_size") == window_size)
        & (pl.col("position").is_in(positions))
        & (pl.col("signal").is_in(signals))
        & (pl.col("now_cost") >= price_range[0] * 10)
        & (pl.col("now_cost") <= price_range[1] * 10)
        & (pl.col("rolling_minutes").is_not_null())
        & (pl.col("rolling_minutes") > 0)
    )

    # Tabs
    tab1, tab2 = st.tabs(["🚀 Attacking Momentum", "🛡️ DEFCON (Defensive)"])

    with tab1:
        # Analysis Guide Expander
        with st.expander("📖 How to read this analysis"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.info(
                    """
                    **What is xG Diff?**
                    * **Negative (-1.5)**: Underperforming. The player is getting chances but not scoring. *Regression to the mean says they are due!*
                    * **Positive (+1.5)**: Overperforming. The player is scoring 'lucky' goals. *Warning: This is often unsustainable.*
                """
                )
            with col_b:
                st.info(
                    """
                    **What is Momentum Score?**
                    * **↗️ Positive (>0.0)**: Underlying numbers (xGI) are improving and consistent.
                    * **↘️ Negative (<0.0)**: Underlying numbers are declining.
                    * *Note: Higher values indicate a steeper, more reliable trend (Slope * R²).*
                """
                )

        # Qualifier: Players must play at least 50% of minutes to be in the "Leaderboard"
        qualified_df = filtered_df.filter(pl.col("minutes_pct") >= 0.5)
        if qualified_df.is_empty():
            qualified_df = filtered_df

        # Top Metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Players Analyzed", len(filtered_df))

        with col2:
            top_buy = (
                filtered_df.filter(pl.col("signal") == "BUY").sort("xg_diff").head(1)
            )
            if not top_buy.is_empty():
                st.metric(
                    "💎 Top Underperformer",
                    top_buy["web_name"][0],
                    f"{top_buy['xg_diff'][0]:.2f} xG Diff",
                    help="The player most 'due' a goal based on chances.",
                )
            else:
                st.metric("Top BUY", "None")

        with col3:
            max_momentum = qualified_df.sort("momentum_score", descending=True).head(1)
            if not max_momentum.is_empty():
                st.metric(
                    "🚀 Rising Star",
                    max_momentum["web_name"][0],
                    f"+{max_momentum['momentum_score'][0]:.4f}",
                    help="The player with the most consistent improvement in expected involvement (xGI).",
                )

        with col4:
            top_sell = (
                filtered_df.filter(pl.col("signal") == "SELL")
                .sort("xg_diff", descending=True)
                .head(1)
            )
            if not top_sell.is_empty():
                st.metric(
                    "⚠️ Sustainability Risk",
                    top_sell["web_name"][0],
                    f"+{top_sell['xg_diff'][0]:.2f} xG Diff",
                    help="The player most likely to stop scoring soon.",
                )
            else:
                st.metric("Risk Alert", "None")

        # Main Visualization
        st.subheader(f"xG vs Actual Goals (Last {window_size} Games)")

        # Create Altair Chart
        chart_data = filtered_df.to_pandas()

        scatter = (
            alt.Chart(chart_data)
            .mark_circle(size=100)
            .encode(
                x=alt.X("rolling_xg:Q", title="Expected Goals (xG)"),
                y=alt.Y("rolling_actual:Q", title="Actual Goals Scored"),
                color=alt.Color(
                    "position:N",
                    scale=alt.Scale(
                        domain=["GKP", "DEF", "MID", "FWD"],
                        range=["#ebff00", "#00ff87", "#05f1ff", "#ff2882"],
                    ),
                ),
                tooltip=[
                    "web_name",
                    "team_name",
                    "position",
                    "rolling_xg",
                    "rolling_actual",
                    "xg_diff",
                    "momentum_score",
                    "signal",
                ],
            )
            .interactive()
        )

        # Diagonal Reference Line (y=x)
        max_val = (
            max(
                float(chart_data["rolling_xg"].max()),
                float(chart_data["rolling_actual"].max()),
            )
            + 0.5
        )
        line = (
            alt.Chart(
                pl.DataFrame({"x": [0.0, max_val], "y": [0.0, max_val]}).to_pandas()
            )
            .mark_line(color="white", strokeDash=[5, 5], opacity=0.3)
            .encode(x="x", y="y")
        )

        st.altair_chart(line + scatter, width="stretch")

        # Data Table
        st.subheader("Deep Dive Analysis")

        # Format for display
        display_df_table = (
            filtered_df.with_columns(
                [
                    (pl.col("now_cost") / 10).alias("Price"),
                    pl.col("xg_diff").round(2),
                    pl.col("momentum_score").round(4),
                    pl.col("xg_per_90").round(2),
                    (pl.col("minutes_pct") * 100)
                    .round(0)
                    .cast(pl.Int64)
                    .alias("Min %"),
                ]
            )
            .select(
                [
                    "web_name",
                    "team_name",
                    "position",
                    "Price",
                    "rolling_xg",
                    "rolling_actual",
                    "xg_diff",
                    "momentum_score",
                    "signal",
                    "Min %",
                ]
            )
            .rename(
                {
                    "web_name": "Name",
                    "team_name": "Team",
                    "rolling_xg": "xG",
                    "rolling_actual": "Goals",
                    "xg_diff": "xG Diff",
                    "momentum_score": "Momentum",
                }
            )
        )

        st.dataframe(display_df_table.sort("xG Diff"), width="stretch", hide_index=True)

    with tab2:
        st.subheader(f"🛡️ DEFCON: Defensive Contribution (Last {window_size} Games)")

        # DEFCON specific filters - Include MID for defensive contributions
        def_df = filtered_df.filter(pl.col("position").is_in(["GKP", "DEF", "MID"]))

        if def_df.is_empty():
            st.warning("No defensive players match the current filters.")
        else:
            # Qualifier: Players must play at least 50% of minutes to be in the "Leaderboard"
            qualified_def = def_df.filter(pl.col("minutes_pct") >= 0.5)

            # If no one meets 50%, fall back to anyone with minutes
            if qualified_def.is_empty():
                qualified_def = def_df

            col_d1, col_d2, col_d3, col_d4 = st.columns(4)
            with col_d1:
                top_defcon = qualified_def.sort("defcon_score", descending=True).head(1)
                st.metric(
                    "🛡️ DEFCON Leader",
                    top_defcon["web_name"][0],
                    f"{top_defcon['defcon_score'][0]:.1f} pts",
                    help="Most defensive actions (Tackles, CBI, Recoveries).",
                )
            with col_d2:
                top_cs = qualified_def.sort("rolling_cs", descending=True).head(1)
                st.metric(
                    "🧤 Clean Sheet King",
                    top_cs["web_name"][0],
                    f"{top_cs['rolling_cs'][0]} CS",
                    help="Most clean sheets in this window.",
                )
            with col_d3:
                low_xgc = qualified_def.sort("rolling_xgc").head(1)
                st.metric(
                    "🧱 Rock Solid (Low xGC)",
                    low_xgc["web_name"][0],
                    f"{low_xgc['rolling_xgc'][0]:.2f} xGC",
                    help="Lowest expected goals conceded (minimum 50% minutes played).",
                )
            with col_d4:
                top_defcon_per90 = qualified_def.sort(
                    "defcon_per_90", descending=True
                ).head(1)
                st.metric(
                    "📈 DEFCON/90 Leader",
                    top_defcon_per90["web_name"][0],
                    f"{top_defcon_per90['defcon_per_90'][0]:.1f} per 90",
                    help="Highest defensive actions per 90 minutes (normalized).",
                )

            # DEFCON Graph
            st.markdown("### Defensive Resilience Graph")
            st.info(
                "**High DEFCON per 90** + **Low xG Conceded** = Best defensive value. DEFCON per 90 normalizes for minutes played."
            )

            def_chart_data = def_df.to_pandas()

            def_scatter = (
                alt.Chart(def_chart_data)
                .mark_circle(size=100)
                .encode(
                    x=alt.X("rolling_xgc:Q", title="Expected Goals Conceded (xGC)"),
                    y=alt.Y(
                        "defcon_per_90:Q",
                        title="DEFCON per 90 (Normalized)",
                    ),
                    color=alt.Color("team_name:N"),
                    tooltip=[
                        "web_name",
                        "team_name",
                        "position",
                        "rolling_cs",
                        "rolling_xgc",
                        "defcon_score",
                        "defcon_per_90",
                    ],
                )
                .interactive()
            )
            st.altair_chart(def_scatter, width="stretch")

            # DEFCON Table
            st.markdown("### Defensive Deep Dive")
            def_display = (
                def_df.with_columns(
                    [
                        (pl.col("now_cost") / 10).alias("Price"),
                        pl.col("defcon_score").round(1),
                        pl.col("rolling_xgc").round(2),
                    ]
                )
                .select(
                    [
                        "web_name",
                        "team_name",
                        "position",
                        "Price",
                        "rolling_cs",
                        "rolling_gc",
                        "rolling_xgc",
                        "defcon_score",
                    ]
                )
                .rename(
                    {
                        "web_name": "Name",
                        "team_name": "Team",
                        "rolling_cs": "CS",
                        "rolling_gc": "GC",
                        "rolling_xgc": "xGC",
                        "defcon_score": "DEFCON",
                    }
                )
                .sort("DEFCON", descending=True)
            )

            st.dataframe(def_display, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
