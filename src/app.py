import streamlit as st
import polars as pl
import altair as alt
from pathlib import Path
from streamlit_option_menu import option_menu

# Constants
DATA_DIR = Path("src/data")
ANALYSIS_FILE = DATA_DIR / "momentum_analysis.parquet"

# Page Config
st.set_page_config(
    page_title="FPL xG Momentum Tracker | Cyber-Pitch",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Cyber-Pitch Theme)
st.markdown(
    """
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
<style>
    /* Global Overrides */
    * {
        font-family: 'Outfit', sans-serif !important;
    }

    .main {
        background-color: #0d1117;
        background-image:
            radial-gradient(at 0% 0%, rgba(0, 255, 135, 0.05) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(255, 40, 130, 0.05) 0px, transparent 50%);
    }

    [data-testid="stSidebar"] {
        background-color: #090c10;
        border-right: 1px solid #30363d;
    }

    /* Metric Cards */
    [data-testid="stMetric"] {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 20px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #00ff87;
    }
    [data-testid="stMetricLabel"] {
        color: #8b949e !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        color: #00ff87 !important;
        font-weight: 800 !important;
        letter-spacing: -1px;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
    }

    /* Header Styling */
    .scoreboard-title {
        background: linear-gradient(90deg, #00ff87 0%, #05f1ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: -2px;
    }
    .subtitle {
        color: #8b949e;
        margin-bottom: 2rem;
        font-size: 1.1rem;
    }

    /* Signal Badges */
    .badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .badge-buy { background-color: #00ff87; color: #0d1117; }
    .badge-hold { background-color: #ffaa00; color: #0d1117; }
    .badge-sell { background-color: #ff2882; color: #ffffff; }

    /* Customizing Streamlit Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: rgba(33, 38, 45, 0.5);
        border-radius: 8px 8px 0px 0px;
        padding: 10px 24px;
        color: #8b949e;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #30363d;
        color: #00ff87;
        font-weight: 800;
    }

    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: #161b22 !important;
        border-radius: 8px !important;
        border: 1px solid #30363d !important;
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
    # Sidebar Logo/Header
    with st.sidebar:
        st.markdown(
            "<h1 style='text-align: center; color: #00ff87;'>⚽ CYBER-PITCH</h1>",
            unsafe_allow_html=True,
        )

        selected = option_menu(
            menu_title=None,
            options=["Attacking", "DefCon", "Scouting"],
            icons=["rocket-takeoff", "shield-lock", "search"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {
                    "padding": "0!important",
                    "background-color": "transparent",
                },
                "icon": {"color": "#00ff87", "font-size": "20px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "0px",
                    "--hover-color": "#161b22",
                    "color": "#8b949e",
                },
                "nav-link-selected": {
                    "background-color": "#30363d",
                    "color": "#00ff87",
                },
            },
        )

        st.divider()
        st.subheader("🛠️ Strategy Engine")

        window_size = st.radio("Rolling Window", [4, 6, 10], index=1, horizontal=True)

        positions = st.multiselect(
            "Positions",
            options=["GKP", "DEF", "MID", "FWD"],
            default=["DEF", "MID", "FWD"],
        )

        signals = st.multiselect(
            "Signals", options=["BUY", "HOLD", "SELL"], default=["BUY", "HOLD", "SELL"]
        )

        display_df = load_data()
        if display_df is not None:
            price_range = st.sidebar.slider(
                "Budget Range (£m)",
                min_value=float(display_df["now_cost"].min() / 10),
                max_value=float(display_df["now_cost"].max() / 10),
                value=(4.0, 15.0),
            )
        else:
            price_range = (4.0, 15.0)

    if display_df is None:
        return

    # Filter Data
    filtered_df = display_df.filter(
        (pl.col("window_size") == window_size)
        & (pl.col("position").is_in(positions))
        & (pl.col("signal").is_in(signals))
        & (pl.col("now_cost") >= price_range[0] * 10)
        & (pl.col("now_cost") <= price_range[1] * 10)
        & (pl.col("rolling_minutes") > 0)
    )

    # Main Header
    st.markdown(
        "<h1 class='scoreboard-title'>FPL Momentum Tracker</h1>", unsafe_allow_html=True
    )
    st.markdown(
        "<p class='subtitle'>Elite-level tactical analysis for serious managers.</p>",
        unsafe_allow_html=True,
    )

    if selected == "Attacking":
        render_attacking_view(filtered_df, window_size)
    elif selected == "DefCon":
        render_defcon_view(filtered_df, window_size)
    elif selected == "Scouting":
        render_scouting_view(filtered_df)


def render_attacking_view(df, window_size):
    # Top Hero Metrics
    qualified_df = df.filter(pl.col("minutes_pct") >= 0.5)
    if qualified_df.is_empty():
        qualified_df = df

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric("Analyzed", len(df), delta=f"{window_size} GM Window")

    with m2:
        top_buy = df.filter(pl.col("signal") == "BUY").sort("xg_diff").head(1)
        if not top_buy.is_empty():
            st.metric(
                "💎 Underperformer",
                top_buy["web_name"][0],
                f"{top_buy['xg_diff'][0]:.2f} xG",
            )
        else:
            st.metric("💎 Underperformer", "N/A")

    with m3:
        max_momentum = qualified_df.sort("momentum_score", descending=True).head(1)
        if not max_momentum.is_empty():
            st.metric(
                "🚀 Rising Star",
                max_momentum["web_name"][0],
                f"+{max_momentum['momentum_score'][0]:.4f}",
            )

    with m4:
        top_sell = (
            df.filter(pl.col("signal") == "SELL")
            .sort("xg_diff", descending=True)
            .head(1)
        )
        if not top_sell.is_empty():
            st.metric(
                "⚠️ Trap Alert",
                top_sell["web_name"][0],
                f"+{top_sell['xg_diff'][0]:.2f} xG",
            )
        else:
            st.metric("⚠️ Trap Alert", "Clear")

    # Visualization
    col_chart, col_guide = st.columns([3, 1])

    with col_chart:
        st.subheader("The Efficiency Matrix")
        chart_data = df.to_pandas()
        scatter = (
            alt.Chart(chart_data)
            .mark_circle(size=120, opacity=0.8, stroke="white", strokeWidth=1)
            .encode(
                x=alt.X("rolling_xg:Q", title="Expected Goals (xG)"),
                y=alt.Y("rolling_actual:Q", title="Actual Goals"),
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
                    "rolling_xg",
                    "rolling_actual",
                    "signal",
                ],
            )
            .interactive()
        )

        # Guide Line
        max_val = (
            max(
                float(chart_data["rolling_xg"].max() or 0),
                float(chart_data["rolling_actual"].max() or 0),
            )
            + 0.5
        )
        line = (
            alt.Chart(
                pl.DataFrame(
                    {"x": [0.0, float(max_val)], "y": [0.0, float(max_val)]}
                ).to_pandas()
            )
            .mark_line(color="#30363d", strokeDash=[5, 5])
            .encode(x="x", y="y")
        )

        st.altair_chart(line + scatter, width="stretch")

    with col_guide:
        st.markdown("#### 📖 Intel")
        st.info(
            "**Efficiency Line**\nAbove line = Overperforming (Trap chance)\nBelow line = Underperforming (Gem chance)"
        )
        st.warning(
            "**Momentum**\nConsistent growth in underlying data (xGI) over the window."
        )

    # Deep Dive Table
    st.subheader("Deep Dive Intelligence")

    # Custom signal formatting for the native dataframe
    # For now, we use simple sorting and clear columns
    table_df = (
        df.with_columns(
            [
                (pl.col("now_cost") / 10).alias("£m"),
                pl.col("xg_diff").round(2),
                pl.col("momentum_score").round(4),
                (pl.col("minutes_pct") * 100).cast(pl.Int64).alias("Min%"),
            ]
        )
        .select(
            [
                "web_name",
                "team_name",
                "position",
                "£m",
                "rolling_xg",
                "rolling_actual",
                "xg_diff",
                "momentum_score",
                "signal",
                "Min%",
            ]
        )
        .sort("xg_diff")
    )

    st.dataframe(
        table_df,
        width="stretch",
        hide_index=True,
        column_config={
            "signal": st.column_config.SelectboxColumn(
                "Status",
                help="Recommended Action",
                options=["BUY", "HOLD", "SELL"],
            ),
            "web_name": "Player",
            "team_name": "Team",
            "rolling_xg": "xG",
            "rolling_actual": "Goals",
            "xg_diff": "xG Diff",
        },
    )


def render_defcon_view(df, window_size):
    def_df = df.filter(pl.col("position").is_in(["GKP", "DEF", "MID"]))
    if def_df.is_empty():
        st.warning("No data found for selective defensive criteria.")
        return

    qualified_def = def_df.filter(pl.col("minutes_pct") >= 0.5)
    if qualified_def.is_empty():
        qualified_def = def_df

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        top_defcon = qualified_def.sort("defcon_score", descending=True).head(1)
        st.metric(
            "🛡️ DEFCON Leader",
            top_defcon["web_name"][0],
            f"{top_defcon['defcon_score'][0]:.1f} pts",
        )
    with d2:
        top_cs = qualified_def.sort("rolling_cs", descending=True).head(1)
        st.metric(
            "🧤 Clean Sheet King",
            top_cs["web_name"][0],
            f"{top_cs['rolling_cs'][0]} CS",
        )
    with d3:
        low_xgc = qualified_def.sort("rolling_xgc").head(1)
        st.metric(
            "🧱 Rock Solid",
            low_xgc["web_name"][0],
            f"{low_xgc['rolling_xgc'][0]:.2f} xGC",
        )
    with d4:
        top_90 = qualified_def.sort("defcon_per_90", descending=True).head(1)
        st.metric(
            "📈 DEFCON/90", top_90["web_name"][0], f"{top_90['defcon_per_90'][0]:.1f}"
        )

    st.subheader("Defensive Resilience Map")
    def_chart = (
        alt.Chart(def_df.to_pandas())
        .mark_circle(size=100)
        .encode(
            x=alt.X("rolling_xgc:Q", title="xG Conceded"),
            y=alt.Y("defcon_per_90:Q", title="Defensive Actions /90"),
            color=alt.Color("team_name:N"),
            tooltip=["web_name", "team_name", "rolling_xgc", "defcon_score"],
        )
        .interactive()
    )
    st.altair_chart(def_chart, width="stretch")

    st.subheader("Defensive Deep Dive Intelligence")
    def_table_df = (
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
        .sort("defcon_score", descending=True)
    )

    st.dataframe(
        def_table_df,
        width="stretch",
        hide_index=True,
        column_config={
            "web_name": "Player",
            "team_name": "Team",
            "rolling_cs": "CS",
            "rolling_gc": "GC",
            "rolling_xgc": "xGC",
            "defcon_score": "DEFCON",
        },
    )


def render_scouting_view(df):
    st.subheader("Elite Player Search")
    query = st.text_input("Search Registry...", placeholder="e.g. Salah, Isak...")

    if query:
        search_results = df.filter(pl.col("web_name").str.contains(f"(?i){query}"))
        if not search_results.is_empty():
            for row in search_results.to_dicts():
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        st.markdown(f"### {row['web_name']}")
                        st.markdown(f"**{row['team_name']} | {row['position']}**")
                    with col2:
                        cols = st.columns(3)
                        cols[0].metric("xG Diff", f"{row['xg_diff']:.2f}")
                        cols[1].metric("Momentum", f"{row['momentum_score']:.3f}")
                        cols[2].metric("DEFCON", f"{row['defcon_score']:.1f}")
                    with col3:
                        signal = row["signal"]
                        st.markdown(
                            f"<div style='text-align:center; padding: 20px; border-radius: 12px; background: #161b22; border: 1px solid #30363d;'>Signal: <br><span class='badge badge-{signal.lower()}'>{signal}</span></div>",
                            unsafe_allow_html=True,
                        )
                    st.divider()
        else:
            st.warning("No matches found in the Cyber-Pitch database.")
    else:
        st.info("Input a player name above to generate a deep tactical report.")


if __name__ == "__main__":
    main()
