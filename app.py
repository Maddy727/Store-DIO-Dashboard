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
    initial_sidebar_state="collapsed"
)

TESCO_BLUE  = "#00539F"
TESCO_RED   = "#E2231A"
GREY        = "#5B6770"
GREEN       = "#2E7D52"
AMBER       = "#C98A0B"
BG_TINT     = "#F4F6F8"

st.markdown(f"""
<style>
    .main {{ background-color: #FFFFFF; }}
    h1, h2, h3 {{ color: #1C1C1C; font-family: 'Georgia', serif; }}
    .tesco-banner {{
        background-color: {TESCO_BLUE};
        color: white;
        padding: 14px 20px;
        border-radius: 8px;
        font-size: 15px;
        font-weight: 600;
        margin-bottom: 18px;
    }}
    .filter-bar {{
        background-color: {BG_TINT};
        padding: 14px 18px;
        border-radius: 8px;
        border: 1px solid #E3E7EA;
        margin-bottom: 18px;
    }}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# MOCK DATA
# ----------------------------------------------------------------------------
@st.cache_data
def generate_store_data():
    random.seed(42)
    np.random.seed(42)
    formats      = ["Hypermarket", "Superstore", "Metro", "Express"]
    regions      = ["London", "South East", "North West", "Scotland", "Midlands", "South West"]
    categories   = ["Fresh Produce", "Bakery", "Chilled", "Frozen", "Ambient Grocery", "Health & Beauty"]
    street_names = ["High St", "Park Rd", "Station Rd", "Mill Lane", "Victoria Rd", "Church St", "Market Sq"]

    rows = []
    for i in range(1, 121):
        fmt    = random.choice(formats)
        region = random.choice(regions)
        target = round(random.uniform(24, 34), 1)
        bias   = {"Hypermarket": 6, "Superstore": 3, "Metro": 0, "Express": -3}[fmt]
        actual = round(max(target + bias + np.random.normal(0, 4), 8), 1)
        variance = round(actual - target, 1)
        trend = [round(actual + np.random.normal(0, 1.5) - (3 - w) * (variance / 8), 1) for w in range(4)]
        excess_cats = random.sample(categories, 2)
        excess_vals = [round(random.uniform(800, 9000), 0) for _ in excess_cats]
        rows.append({
            "store_id":    f"TS{1000 + i}",
            "store_name":  f"Tesco {fmt} {random.choice(street_names)} {i}",
            "format":      fmt,
            "region":      region,
            "dio_days":    actual,
            "dio_target":  target,
            "dio_variance": variance,
            "trend_w1": trend[0], "trend_w2": trend[1],
            "trend_w3": trend[2], "trend_w4": trend[3],
            "excess_cat_1": excess_cats[0], "excess_val_1": excess_vals[0],
            "excess_cat_2": excess_cats[1], "excess_val_2": excess_vals[1],
        })

    df = pd.DataFrame(rows)
    df["rank_in_region"] = df.groupby("region")["dio_variance"].rank(ascending=False, method="min").astype(int)
    df["status"] = np.where(df["dio_variance"] > 4, "🔴 High Risk",
                   np.where(df["dio_variance"] > 1.5, "🟡 Watch", "🟢 On Target"))
    return df

df = generate_store_data()

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
st.markdown("## 📦 Store DIO Scorecard — Tesco")
st.markdown(f"<p style='color:{GREY}; font-size:15px; margin-top:-10px;'>Rank stores vs. peers weekly · Direct coaching attention · Release working capital</p>", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# FILTER BAR — inline at the top, immediately visible
# ----------------------------------------------------------------------------
st.markdown("<div class='filter-bar'>", unsafe_allow_html=True)
st.markdown("**🔍 Filter Stores**")
fc1, fc2, fc3 = st.columns(3)

with fc1:
    region_options = sorted(df["region"].unique())
    region_filter  = st.multiselect("Region", region_options, default=region_options, key="region")

with fc2:
    format_options = sorted(df["format"].unique())
    format_filter  = st.multiselect("Store Format", format_options, default=format_options, key="format")

with fc3:
    status_options = ["🔴 High Risk", "🟡 Watch", "🟢 On Target"]
    status_filter  = st.multiselect("Status", status_options, default=status_options, key="status")

st.markdown("</div>", unsafe_allow_html=True)

# Apply filters
filtered = df[
    df["region"].isin(region_filter) &
    df["format"].isin(format_filter) &
    df["status"].isin(status_filter)
]

# ----------------------------------------------------------------------------
# EXECUTIVE BANNER
# ----------------------------------------------------------------------------
high_risk_n = len(filtered[filtered["status"] == "🔴 High Risk"])
st.markdown(
    f"<div class='tesco-banner'>⚡ Executive Takeaway: "
    f"<b>{high_risk_n} stores</b> are currently High Risk on DIO across your selected filters — "
    f"prioritising the top 10 could release meaningful working capital this quarter.</div>",
    unsafe_allow_html=True
)

# ----------------------------------------------------------------------------
# KPI CARDS
# ----------------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Average Store DIO",   f"{filtered['dio_days'].mean():.1f} days",
          f"{filtered['dio_variance'].mean():+.1f} vs target")
k2.metric("Average DIO Target",  f"{filtered['dio_target'].mean():.1f} days")
k3.metric("🔴 High Risk Stores", f"{high_risk_n}",
          f"of {len(filtered)} stores shown")
k4.metric("🟢 On Target Stores", f"{len(filtered[filtered['status']=='🟢 On Target'])}",
          f"{len(filtered[filtered['status']=='🟢 On Target'])/max(len(filtered),1)*100:.0f}% of total")

st.markdown("<br>", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# CHARTS
# ----------------------------------------------------------------------------
ch1, ch2 = st.columns([1.4, 1])

with ch1:
    st.subheader("DIO Variance by Region")
    region_summary = (filtered.groupby("region", as_index=False)["dio_variance"]
                      .mean().sort_values("dio_variance", ascending=False))
    fig_bar = px.bar(
        region_summary, x="region", y="dio_variance",
        color="dio_variance",
        color_continuous_scale=[[0, GREEN], [0.4, AMBER], [1, TESCO_RED]],
        labels={"dio_variance": "Avg DIO Variance (days)", "region": "Region"}
    )
    fig_bar.update_layout(coloraxis_showscale=False, height=340, margin=dict(t=10, b=10))
    st.plotly_chart(fig_bar, width="stretch")

with ch2:
    st.subheader("Store Status Mix")
    sc = filtered["status"].value_counts().reindex(status_options).fillna(0)
    fig_pie = px.pie(
        names=sc.index, values=sc.values,
        color=sc.index,
        color_discrete_map={
            "🔴 High Risk": TESCO_RED,
            "🟡 Watch":     AMBER,
            "🟢 On Target": GREEN
        },
        hole=0.5
    )
    fig_pie.update_layout(height=340, margin=dict(t=10, b=10))
    st.plotly_chart(fig_pie, width="stretch")

# ----------------------------------------------------------------------------
# LEADERBOARD TABLE
# ----------------------------------------------------------------------------
st.markdown("---")
st.subheader("📊 Store Leaderboard — Highest DIO Variance First")
st.caption("Click any column header to re-sort. Stores with the largest gap above target are highest-priority coaching candidates.")

display_df = (
    filtered.sort_values("dio_variance", ascending=False)
    [[  "store_name","region","format","dio_days","dio_target","dio_variance","status","rank_in_region"]]
    .rename(columns={
        "store_name":    "Store",
        "region":        "Region",
        "format":        "Format",
        "dio_days":      "DIO (days)",
        "dio_target":    "Target (days)",
        "dio_variance":  "Variance (days)",
        "status":        "Status",
        "rank_in_region":"Rank in Region"
    })
    .reset_index(drop=True)
)

def colour_variance(val):
    if val > 4:   return f"color: {TESCO_RED}; font-weight: bold;"
    elif val > 1.5: return f"color: {AMBER}; font-weight: bold;"
    else:           return f"color: {GREEN}; font-weight: bold;"

styled = display_df.style.map(colour_variance, subset=["Variance (days)"])

st.dataframe(styled, use_container_width=True, height=400)

# ----------------------------------------------------------------------------
# STORE DRILL-DOWN
# ----------------------------------------------------------------------------
st.markdown("---")
st.subheader("🔎 Store Drill-Down")

if len(filtered) == 0:
    st.warning("No stores match your current filters. Please adjust the dropdowns above.")
else:
    selected_store = st.selectbox(
        "Select a store to inspect in detail",
        filtered.sort_values("dio_variance", ascending=False)["store_name"].values
    )
    row = filtered[filtered["store_name"] == selected_store].iloc[0]

    d1, d2 = st.columns([1, 1.4])

    with d1:
        st.markdown(f"### {row['store_name']}")
        st.markdown(f"**Region:** {row['region']}  |  **Format:** {row['format']}")
        st.metric("Current DIO",    f"{row['dio_days']} days", f"{row['dio_variance']:+.1f} days vs target")
        st.metric("Target DIO",     f"{row['dio_target']} days")
        st.metric("Rank in Region", f"#{row['rank_in_region']}")
        st.markdown(f"**Status:** {row['status']}")
        st.markdown("##### 🗂 Top Excess Inventory Categories")
        st.markdown(f"- **{row['excess_cat_1']}** — £{row['excess_val_1']:,.0f} tied up")
        st.markdown(f"- **{row['excess_cat_2']}** — £{row['excess_val_2']:,.0f} tied up")

    with d2:
        trend_df = pd.DataFrame({
            "Week": ["Week −3", "Week −2", "Week −1", "This Week"],
            "DIO":  [row["trend_w1"], row["trend_w2"], row["trend_w3"], row["trend_w4"]]
        })
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=trend_df["Week"], y=trend_df["DIO"],
            mode="lines+markers",
            line=dict(color=TESCO_BLUE, width=3),
            marker=dict(size=10, color=TESCO_BLUE),
            name="DIO"
        ))
        fig_trend.add_hline(
            y=row["dio_target"], line_dash="dash", line_color=GREY,
            annotation_text=f"Target ({row['dio_target']} days)",
            annotation_position="bottom right"
        )
        fig_trend.update_layout(
            title="4-Week DIO Trend",
            yaxis_title="DIO (days)",
            height=340,
            margin=dict(t=40, b=10)
        )
        st.plotly_chart(fig_trend, use_container_width=True)

st.markdown("---")
st.caption("Tesco | AI & Advanced Analytics for Working Capital Optimisation — Store DIO Scorecard (Demo Data)")
