import streamlit as st
import pandas as pd
import numpy as np
import random
import plotly.express as px
import plotly.graph_objects as go

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Store DIO Scorecard | Tesco",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------------------------------------------------------
# TESCO BRAND COLORS
# ----------------------------------------------------------------------------
TESCO_BLUE = "#00539F"
TESCO_RED = "#E2231A"
GREY = "#5B6770"
GREEN = "#2E7D52"
AMBER = "#C98A0B"
BG_TINT = "#F4F6F8"

# ----------------------------------------------------------------------------
# CUSTOM CSS — gives it a clean, branded, consulting-deck look
# ----------------------------------------------------------------------------
st.markdown(f"""
<style>
    .main {{ background-color: #FFFFFF; }}
    .stMetric {{
        background-color: {BG_TINT};
        border: 1px solid #E3E7EA;
        border-radius: 10px;
        padding: 14px 10px 6px 10px;
    }}
    h1, h2, h3 {{ color: #1C1C1C; font-family: 'Georgia', serif; }}
    .tesco-banner {{
        background-color: {TESCO_BLUE};
        color: white;
        padding: 14px 20px;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 20px;
    }}
    .stDataFrame {{ border: 1px solid #E3E7EA; border-radius: 8px; }}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# MOCK DATA GENERATION (cached so it doesn't regenerate on every click)
# ----------------------------------------------------------------------------
@st.cache_data
def generate_store_data(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)

    formats = ["Hypermarket", "Superstore", "Metro", "Express"]
    regions = ["London", "South East", "North West", "Scotland", "Midlands", "South West"]
    categories = ["Fresh Produce", "Bakery", "Chilled", "Frozen", "Ambient Grocery", "Health & Beauty"]
    street_names = ["High St", "Park Rd", "Station Rd", "Mill Lane", "Victoria Rd", "Church St", "Market Sq"]

    rows = []
    for i in range(1, 121):
        fmt = random.choice(formats)
        region = random.choice(regions)
        target = round(random.uniform(24, 34), 1)
        # Hypermarkets tend to run higher DIO; Express lower
        bias = {"Hypermarket": 6, "Superstore": 3, "Metro": 0, "Express": -3}[fmt]
        actual = round(target + bias + np.random.normal(0, 4), 1)
        actual = max(actual, 8)
        variance = round(actual - target, 1)

        trend = [round(actual + np.random.normal(0, 1.5) - (3 - w) * (variance / 8), 1) for w in range(4)]

        excess_cats = random.sample(categories, 2)
        excess_vals = [round(random.uniform(800, 9000), 0) for _ in excess_cats]

        rows.append({
            "store_id": f"TS{1000 + i}",
            "store_name": f"Tesco {fmt} {random.choice(street_names)} {i}",
            "format": fmt,
            "region": region,
            "dio_days": actual,
            "dio_target": target,
            "dio_variance": variance,
            "trend_w1": trend[0], "trend_w2": trend[1], "trend_w3": trend[2], "trend_w4": trend[3],
            "excess_cat_1": excess_cats[0], "excess_val_1": excess_vals[0],
            "excess_cat_2": excess_cats[1], "excess_val_2": excess_vals[1],
        })

    df = pd.DataFrame(rows)
    df["rank_in_region"] = df.groupby("region")["dio_variance"].rank(ascending=False, method="min").astype(int)
    df["status"] = np.where(df["dio_variance"] > 4, "High Risk",
                      np.where(df["dio_variance"] > 1.5, "Watch", "On Target"))
    return df

df = generate_store_data()

# ----------------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------------
st.sidebar.markdown("## 🔍 Filters")
region_filter = st.sidebar.multiselect("Region", sorted(df["region"].unique()), default=sorted(df["region"].unique()))
format_filter = st.sidebar.multiselect("Store Format", sorted(df["format"].unique()), default=sorted(df["format"].unique()))
status_filter = st.sidebar.multiselect("Status", ["High Risk", "Watch", "On Target"], default=["High Risk", "Watch", "On Target"])

st.sidebar.markdown("---")
st.sidebar.markdown("##### About this dashboard")
st.sidebar.caption(
    "Mock data for demonstration purposes. In production, this connects to live "
    "store-level inventory, sales and delivery feeds, refreshed daily."
)

filtered = df[
    df["region"].isin(region_filter) &
    df["format"].isin(format_filter) &
    df["status"].isin(status_filter)
]

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
st.markdown(f"<h1 style='margin-bottom:0px;'>📦 Store DIO Scorecard</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:{GREY}; font-size:16px; margin-top:0px;'>Rank stores vs. peers weekly to direct coaching attention and release working capital</p>", unsafe_allow_html=True)

st.markdown(
    f"<div class='tesco-banner'>Executive takeaway: {len(filtered[filtered['status']=='High Risk'])} stores are currently High Risk on DIO — "
    f"prioritizing the top 10 could release meaningful working capital this quarter.</div>",
    unsafe_allow_html=True
)

# ----------------------------------------------------------------------------
# KPI ROW
# ----------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
avg_dio = filtered["dio_days"].mean()
avg_target = filtered["dio_target"].mean()
avg_variance = filtered["dio_variance"].mean()
high_risk_count = len(filtered[filtered["status"] == "High Risk"])

col1.metric("Average Store DIO", f"{avg_dio:.1f} days", f"{avg_variance:+.1f} vs target")
col2.metric("Average Target DIO", f"{avg_target:.1f} days")
col3.metric("High Risk Stores", f"{high_risk_count}", f"of {len(filtered)} stores")
col4.metric("Stores On Target", f"{len(filtered[filtered['status']=='On Target'])}", f"{len(filtered[filtered['status']=='On Target'])/max(len(filtered),1)*100:.0f}%")

st.markdown("<br>", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# CHARTS ROW
# ----------------------------------------------------------------------------
chart_col1, chart_col2 = st.columns([1.3, 1])

with chart_col1:
    st.subheader("DIO Variance by Region")
    region_summary = filtered.groupby("region", as_index=False)["dio_variance"].mean().sort_values("dio_variance", ascending=False)
    fig_region = px.bar(
        region_summary, x="region", y="dio_variance",
        color="dio_variance", color_continuous_scale=[GREEN, AMBER, TESCO_RED],
        labels={"dio_variance": "Avg DIO Variance (days)", "region": "Region"}
    )
    fig_region.update_layout(showlegend=False, coloraxis_showscale=False, height=360, margin=dict(t=10))
    st.plotly_chart(fig_region, use_container_width=True)

with chart_col2:
    st.subheader("Store Status Mix")
    status_counts = filtered["status"].value_counts().reindex(["High Risk", "Watch", "On Target"]).fillna(0)
    fig_pie = px.pie(
        names=status_counts.index, values=status_counts.values,
        color=status_counts.index,
        color_discrete_map={"High Risk": TESCO_RED, "Watch": AMBER, "On Target": GREEN},
        hole=0.5
    )
    fig_pie.update_layout(height=360, margin=dict(t=10))
    st.plotly_chart(fig_pie, use_container_width=True)

# ----------------------------------------------------------------------------
# LEADERBOARD TABLE
# ----------------------------------------------------------------------------
st.subheader("📊 Store Leaderboard — Highest DIO Variance First")
st.caption("Stores with the largest gap above target are the highest-priority coaching candidates.")

display_df = filtered.sort_values("dio_variance", ascending=False)[[
    "store_name", "region", "format", "dio_days", "dio_target", "dio_variance", "status", "rank_in_region"
]].rename(columns={
    "store_name": "Store", "region": "Region", "format": "Format",
    "dio_days": "DIO (days)", "dio_target": "Target (days)",
    "dio_variance": "Variance (days)", "status": "Status", "rank_in_region": "Rank in Region"
})

def highlight_status(val):
    color_map = {"High Risk": f"background-color: #FBE7E6; color: {TESCO_RED};",
                 "Watch": f"background-color: #FCF3E5; color: {AMBER};",
                 "On Target": f"background-color: #EFF6F1; color: {GREEN};"}
    return color_map.get(val, "")

st.dataframe(
    display_df.style.applymap(highlight_status, subset=["Status"]),
    use_container_width=True,
    height=420
)

# ----------------------------------------------------------------------------
# STORE DRILL-DOWN
# ----------------------------------------------------------------------------
st.markdown("---")
st.subheader("🔎 Store Drill-Down")

selected_store = st.selectbox("Select a store to inspect", filtered["store_name"].sort_values())
store_row = filtered[filtered["store_name"] == selected_store].iloc[0]

dcol1, dcol2 = st.columns([1, 1.3])

with dcol1:
    st.markdown(f"**{store_row['store_name']}**")
    st.markdown(f"Region: **{store_row['region']}**  |  Format: **{store_row['format']}**")
    st.metric("Current DIO", f"{store_row['dio_days']} days", f"{store_row['dio_variance']:+.1f} vs target")
    st.markdown(f"**Status:** {store_row['status']}")
    st.markdown(f"**Rank in Region:** #{store_row['rank_in_region']}")
    st.markdown("##### Top Excess Categories")
    st.markdown(f"- {store_row['excess_cat_1']}: £{store_row['excess_val_1']:,.0f} tied up")
    st.markdown(f"- {store_row['excess_cat_2']}: £{store_row['excess_val_2']:,.0f} tied up")

with dcol2:
    trend_data = pd.DataFrame({
        "Week": ["Week -3", "Week -2", "Week -1", "This Week"],
        "DIO": [store_row["trend_w1"], store_row["trend_w2"], store_row["trend_w3"], store_row["trend_w4"]]
    })
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend_data["Week"], y=trend_data["DIO"], mode="lines+markers",
        line=dict(color=TESCO_BLUE, width=3), marker=dict(size=9)
    ))
    fig_trend.add_hline(y=store_row["dio_target"], line_dash="dash", line_color=GREY,
                         annotation_text="Target", annotation_position="bottom right")
    fig_trend.update_layout(title="4-Week DIO Trend", height=320, margin=dict(t=40))
    st.plotly_chart(fig_trend, use_container_width=True)

st.markdown("---")
st.caption("Tesco | AI & Advanced Analytics for Working Capital Optimization — Store DIO Scorecard (Demo)")
