import streamlit as st
import pandas as pd
import numpy as np
import random
import plotly.express as px
import plotly.graph_objects as go

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Store DIO Scorecard | Tesco",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

TESCO_BLUE = "#00539F"
TESCO_RED  = "#E2231A"
GREY       = "#5B6770"
GREEN      = "#2E7D52"
AMBER      = "#C98A0B"
BG_TINT    = "#F4F6F8"

st.markdown(f"""
<style>
    .main {{ background-color:#FFFFFF; }}
    h1,h2,h3 {{ color:#1C1C1C; font-family:'Georgia',serif; }}
    .tesco-banner {{
        background-color:{TESCO_BLUE}; color:white;
        padding:14px 20px; border-radius:8px;
        font-size:15px; font-weight:600; margin-bottom:18px;
    }}
    .filter-bar {{
        background-color:{BG_TINT}; padding:14px 18px;
        border-radius:8px; border:1px solid #E3E7EA; margin-bottom:18px;
    }}
    .insight-card {{
        background-color:{BG_TINT}; border-left:4px solid {TESCO_RED};
        padding:12px 16px; border-radius:6px; margin-bottom:10px;
    }}
    .action-card {{
        background-color:#EFF6F1; border-left:4px solid {GREEN};
        padding:12px 16px; border-radius:6px; margin-bottom:10px;
    }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MOCK DATA — stores, categories, SKUs
# ─────────────────────────────────────────────────────────────────────────────
CATEGORIES = [
    "Fresh Produce", "Bakery", "Chilled Dairy", "Frozen",
    "Ambient Grocery", "Health & Beauty", "Beers Wine Spirits",
    "Seasonal / Gifting"
]

SKU_POOL = {
    "Fresh Produce":       ["Strawberries 400g", "Bag Salad Mixed", "Broccoli Each", "Cherry Tomatoes 250g", "Avocado Each"],
    "Bakery":              ["White Sliced 800g", "Seeded Batch Loaf", "All-Butter Croissant 4pk", "Tiger Bloomer", "Pain au Chocolat 4pk"],
    "Chilled Dairy":       ["Whole Milk 4pt", "Greek Yoghurt 500g", "Cheddar Mature 400g", "Butter Unsalted 250g", "Cream Cheese 200g"],
    "Frozen":              ["Garden Peas 900g", "Chips Straight Cut 1kg", "Fish Fingers 12pk", "Oven Pizza Marg", "Mixed Veg 1kg"],
    "Ambient Grocery":     ["Baked Beans 4pk", "Pasta Penne 500g", "Tomato Sauce Jar 500g", "Rice Basmati 1kg", "Coffee Granules 200g"],
    "Health & Beauty":     ["Shampoo 500ml", "Body Wash 250ml", "Toothpaste 75ml", "Hand Cream 75ml", "Face Wash 150ml"],
    "Beers Wine Spirits":  ["Lager 18pk", "Rose Wine 75cl", "Prosecco 75cl", "Cider 4pk", "Red Wine 75cl"],
    "Seasonal / Gifting":  ["Easter Egg Lg", "Xmas Selection Box", "Valentine Choc Box", "Mother's Day Flowers", "Gift Wrap Bundle"],
}

REPLEN_ACTIONS = ["Reduce Order Qty", "Increase Frequency", "Markdown & Clear", "Transfer to Another Store", "Review Par Level"]

@st.cache_data
def generate_all_data():
    random.seed(42); np.random.seed(42)
    formats      = ["Hypermarket","Superstore","Metro","Express"]
    regions      = ["London","South East","North West","Scotland","Midlands","South West"]
    street_names = ["High St","Park Rd","Station Rd","Mill Lane","Victoria Rd","Church St","Market Sq"]

    # ── Store-level ──────────────────────────────────────────────────────────
    stores = []
    for i in range(1, 121):
        fmt    = random.choice(formats)
        region = random.choice(regions)
        target = round(random.uniform(24, 34), 1)
        bias   = {"Hypermarket":6,"Superstore":3,"Metro":0,"Express":-3}[fmt]
        actual = round(max(target + bias + np.random.normal(0, 4), 8), 1)
        variance = round(actual - target, 1)
        trend = [round(actual + np.random.normal(0,1.5) - (3-w)*(variance/8), 1) for w in range(4)]
        stores.append({
            "store_id":   f"TS{1000+i}",
            "store_name": f"Tesco {fmt} {random.choice(street_names)} {i}",
            "format": fmt, "region": region,
            "dio_days": actual, "dio_target": target, "dio_variance": variance,
            "trend_w1":trend[0],"trend_w2":trend[1],"trend_w3":trend[2],"trend_w4":trend[3],
        })
    store_df = pd.DataFrame(stores)
    store_df["rank_in_region"] = store_df.groupby("region")["dio_variance"].rank(ascending=False, method="min").astype(int)
    store_df["status"] = np.where(store_df["dio_variance"]>4,"🔴 High Risk",
                          np.where(store_df["dio_variance"]>1.5,"🟡 Watch","🟢 On Target"))

    # ── Category-level (per store) ───────────────────────────────────────────
    cat_rows = []
    for _, s in store_df.iterrows():
        for cat in CATEGORIES:
            cat_bias = {
                "Fresh Produce":2.5,"Bakery":1.2,"Chilled Dairy":0.8,"Frozen":3.1,
                "Ambient Grocery":1.8,"Health & Beauty":4.2,"Beers Wine Spirits":5.0,
                "Seasonal / Gifting":7.0
            }[cat]
            cat_dio  = round(max(s["dio_days"] + cat_bias + np.random.normal(0, 2.5), 3), 1)
            cat_tgt  = round(s["dio_target"] + cat_bias * 0.6, 1)
            cat_var  = round(cat_dio - cat_tgt, 1)
            inv_val  = round(random.uniform(2000, 45000), 0)
            excess   = round(max(cat_var, 0) / max(cat_dio, 1) * inv_val, 0)
            cat_rows.append({
                "store_id": s["store_id"], "store_name": s["store_name"],
                "category": cat,
                "cat_dio": cat_dio, "cat_target": cat_tgt, "cat_variance": cat_var,
                "inventory_value_gbp": inv_val,
                "excess_value_gbp": excess,
                "weeks_cover": round(cat_dio / 7, 1),
            })
    cat_df = pd.DataFrame(cat_rows)

    # ── SKU-level (top offenders per store per category) ────────────────────
    sku_rows = []
    for _, s in store_df.iterrows():
        for cat in CATEGORIES:
            skus = SKU_POOL[cat]
            for sku in skus:
                sku_dio      = round(max(np.random.normal(28, 9), 4), 1)
                sku_target   = round(random.uniform(18, 28), 1)
                sku_variance = round(sku_dio - sku_target, 1)
                sku_stock    = round(random.uniform(20, 400), 0)
                daily_sales  = round(random.uniform(2, 40), 1)
                weeks_cover  = round(sku_stock / max(daily_sales * 7, 1), 1)
                excess_units = round(max((sku_dio - sku_target) / 7 * daily_sales, 0), 0)
                excess_gbp   = round(excess_units * random.uniform(0.5, 8.0), 0)
                action       = (
                    "Markdown & Clear"           if sku_variance > 10 else
                    "Reduce Order Qty"           if sku_variance > 5  else
                    "Increase Frequency"         if sku_variance > 2  else
                    "Transfer to Another Store"  if sku_variance > 0  else
                    "Review Par Level"
                )
                sku_rows.append({
                    "store_id": s["store_id"], "store_name": s["store_name"],
                    "category": cat, "sku_name": sku,
                    "sku_dio": sku_dio, "sku_target": sku_target,
                    "sku_variance": sku_variance,
                    "stock_units": int(sku_stock),
                    "daily_sales_units": daily_sales,
                    "weeks_cover": weeks_cover,
                    "excess_units": int(excess_units),
                    "excess_value_gbp": excess_gbp,
                    "recommended_action": action,
                })
    sku_df = pd.DataFrame(sku_rows)

    return store_df, cat_df, sku_df

store_df, cat_df, sku_df = generate_all_data()

# ─────────────────────────────────────────────────────────────────────────────
# TABS — keeps the layout clean across multiple insight levels
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("## 📦 Store DIO Scorecard — Tesco")
st.markdown(f"<p style='color:{GREY};font-size:15px;margin-top:-10px;'>Rank stores vs. peers · Identify category root causes · Prioritise SKU-level replenishment actions</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🏪 Store Overview", "📂 Category Deep-Dive", "🔬 SKU Replenishment Actions"])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — STORE OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    # Filters
    st.markdown("<div class='filter-bar'>", unsafe_allow_html=True)
    st.markdown("**🔍 Filter Stores**")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        region_opts   = sorted(store_df["region"].unique())
        region_filter = st.multiselect("Region", region_opts, default=region_opts, key="t1_region")
    with fc2:
        format_opts   = sorted(store_df["format"].unique())
        format_filter = st.multiselect("Store Format", format_opts, default=format_opts, key="t1_format")
    with fc3:
        status_opts   = ["🔴 High Risk","🟡 Watch","🟢 On Target"]
        status_filter = st.multiselect("Status", status_opts, default=status_opts, key="t1_status")
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = store_df[
        store_df["region"].isin(region_filter) &
        store_df["format"].isin(format_filter) &
        store_df["status"].isin(status_filter)
    ]

    high_risk_n = len(filtered[filtered["status"]=="🔴 High Risk"])
    st.markdown(f"<div class='tesco-banner'>⚡ <b>{high_risk_n} stores</b> are High Risk on DIO across your selected filters — use the Category and SKU tabs to find the root cause.</div>", unsafe_allow_html=True)

    # KPIs
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Avg Store DIO",        f"{filtered['dio_days'].mean():.1f} days", f"{filtered['dio_variance'].mean():+.1f} vs target")
    k2.metric("Avg DIO Target",       f"{filtered['dio_target'].mean():.1f} days")
    k3.metric("🔴 High Risk Stores",  str(high_risk_n), f"of {len(filtered)} stores")
    k4.metric("🟢 On Target Stores",  str(len(filtered[filtered["status"]=="🟢 On Target"])),
              f"{len(filtered[filtered['status']=='🟢 On Target'])/max(len(filtered),1)*100:.0f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    ch1, ch2 = st.columns([1.4, 1])
    with ch1:
        st.subheader("DIO Variance by Region")
        reg_sum = filtered.groupby("region",as_index=False)["dio_variance"].mean().sort_values("dio_variance",ascending=False)
        fig_bar = px.bar(reg_sum, x="region", y="dio_variance",
                         color="dio_variance", color_continuous_scale=[[0,GREEN],[0.4,AMBER],[1,TESCO_RED]],
                         labels={"dio_variance":"Avg DIO Variance (days)","region":"Region"})
        fig_bar.update_layout(coloraxis_showscale=False, height=320, margin=dict(t=10,b=10))
        st.plotly_chart(fig_bar, use_container_width=True)
    with ch2:
        st.subheader("Store Status Mix")
        sc = filtered["status"].value_counts().reindex(status_opts).fillna(0)
        fig_pie = px.pie(names=sc.index, values=sc.values, hole=0.5,
                         color=sc.index, color_discrete_map={"🔴 High Risk":TESCO_RED,"🟡 Watch":AMBER,"🟢 On Target":GREEN})
        fig_pie.update_layout(height=320, margin=dict(t=10,b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    # Leaderboard
    st.markdown("---")
    st.subheader("📊 Store Leaderboard — Highest DIO Variance First")
    disp = (filtered.sort_values("dio_variance",ascending=False)
            [["store_name","region","format","dio_days","dio_target","dio_variance","status","rank_in_region"]]
            .rename(columns={"store_name":"Store","region":"Region","format":"Format",
                             "dio_days":"DIO (days)","dio_target":"Target (days)",
                             "dio_variance":"Variance (days)","status":"Status","rank_in_region":"Rank in Region"})
            .reset_index(drop=True))
    def colour_var(v):
        if v>4:   return f"color:{TESCO_RED};font-weight:bold;"
        elif v>1.5: return f"color:{AMBER};font-weight:bold;"
        return f"color:{GREEN};font-weight:bold;"
    st.dataframe(disp.style.map(colour_var, subset=["Variance (days)"]), use_container_width=True, height=380)

    # Drill-down
    st.markdown("---")
    st.subheader("🔎 Store Drill-Down")
    if len(filtered)==0:
        st.warning("No stores match your filters.")
    else:
        sel = st.selectbox("Select a store", filtered.sort_values("dio_variance",ascending=False)["store_name"].values, key="t1_store")
        row = filtered[filtered["store_name"]==sel].iloc[0]
        d1,d2 = st.columns([1,1.4])
        with d1:
            st.markdown(f"### {row['store_name']}")
            st.markdown(f"**Region:** {row['region']}  |  **Format:** {row['format']}")
            st.metric("Current DIO", f"{row['dio_days']} days", f"{row['dio_variance']:+.1f} vs target")
            st.metric("Rank in Region", f"#{row['rank_in_region']}")
            st.markdown(f"**Status:** {row['status']}")
            st.info("👉 Go to the **Category Deep-Dive** tab to see which categories are driving this store's DIO.")
        with d2:
            td = pd.DataFrame({"Week":["Week −3","Week −2","Week −1","This Week"],
                                "DIO":[row["trend_w1"],row["trend_w2"],row["trend_w3"],row["trend_w4"]]})
            fig_t = go.Figure()
            fig_t.add_trace(go.Scatter(x=td["Week"],y=td["DIO"],mode="lines+markers",
                                        line=dict(color=TESCO_BLUE,width=3),marker=dict(size=10)))
            fig_t.add_hline(y=row["dio_target"],line_dash="dash",line_color=GREY,
                             annotation_text=f"Target ({row['dio_target']} days)",annotation_position="bottom right")
            fig_t.update_layout(title="4-Week DIO Trend",yaxis_title="DIO (days)",height=320,margin=dict(t=40,b=10))
            st.plotly_chart(fig_t, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — CATEGORY DEEP-DIVE
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📂 Category Deep-Dive — What Is Driving High DIO?")
    st.caption("Select a store to see which product categories are locking the most cash, ranked by DIO variance.")

    c1, c2 = st.columns(2)
    with c1:
        all_stores = store_df.sort_values("dio_variance",ascending=False)["store_name"].values
        sel_store2 = st.selectbox("Select Store", all_stores, key="t2_store")
    with c2:
        view_mode = st.radio("View by", ["DIO Variance vs Target", "Excess Inventory Value (£)"], horizontal=True)

    store_id2  = store_df[store_df["store_name"]==sel_store2]["store_id"].values[0]
    store_cats = cat_df[cat_df["store_id"]==store_id2].sort_values("cat_variance",ascending=False)
    store_row2 = store_df[store_df["store_id"]==store_id2].iloc[0]

    # Banner
    top_cat    = store_cats.iloc[0]["category"]
    top_excess = store_cats["excess_value_gbp"].sum()
    st.markdown(f"<div class='insight-card'>🔍 <b>Root cause insight:</b> For <b>{sel_store2}</b>, "
                f"<b>{top_cat}</b> has the highest DIO variance. Total estimated excess inventory across all categories: "
                f"<b>£{top_excess:,.0f}</b></div>", unsafe_allow_html=True)

    # Charts
    ch1, ch2 = st.columns([1.4, 1])

    with ch1:
        if view_mode == "DIO Variance vs Target":
            fig_cat = px.bar(
                store_cats.sort_values("cat_variance"), x="cat_variance", y="category",
                orientation="h", color="cat_variance",
                color_continuous_scale=[[0,GREEN],[0.35,AMBER],[1,TESCO_RED]],
                labels={"cat_variance":"DIO Variance (days)","category":"Category"},
                title="DIO Variance by Category"
            )
            fig_cat.add_vline(x=0, line_dash="dash", line_color=GREY)
        else:
            fig_cat = px.bar(
                store_cats.sort_values("excess_value_gbp"), x="excess_value_gbp", y="category",
                orientation="h", color="excess_value_gbp",
                color_continuous_scale=[[0,GREEN],[0.35,AMBER],[1,TESCO_RED]],
                labels={"excess_value_gbp":"Excess Inventory Value (£)","category":"Category"},
                title="Excess Inventory by Category (£)"
            )
        fig_cat.update_layout(coloraxis_showscale=False, height=380, margin=dict(t=40,b=10))
        st.plotly_chart(fig_cat, use_container_width=True)

    with ch2:
        # Heatmap: category DIO vs store target
        fig_gauge = go.Figure(go.Bar(
            x=store_cats["cat_dio"],
            y=store_cats["category"],
            orientation="h",
            marker_color=[TESCO_RED if v>4 else AMBER if v>1.5 else GREEN for v in store_cats["cat_variance"]],
            text=[f"{v:+.1f}d" for v in store_cats["cat_variance"]],
            textposition="outside"
        ))
        fig_gauge.add_vline(x=store_row2["dio_target"], line_dash="dash", line_color=GREY,
                             annotation_text="Store Target", annotation_position="top right")
        fig_gauge.update_layout(title="Category DIO vs Store Target", xaxis_title="DIO (days)",
                                 height=380, margin=dict(t=40,b=10))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # Category detail table
    st.markdown("---")
    st.subheader("Category Summary Table")
    cat_disp = store_cats[["category","cat_dio","cat_target","cat_variance","weeks_cover","inventory_value_gbp","excess_value_gbp"]].rename(columns={
        "category":"Category","cat_dio":"DIO (days)","cat_target":"Target (days)",
        "cat_variance":"Variance (days)","weeks_cover":"Weeks Cover",
        "inventory_value_gbp":"Total Inv. Value (£)","excess_value_gbp":"Est. Excess (£)"
    }).reset_index(drop=True)

    def colour_cat_var(v):
        if v>4:    return f"color:{TESCO_RED};font-weight:bold;"
        elif v>1.5: return f"color:{AMBER};font-weight:bold;"
        return f"color:{GREEN};font-weight:bold;"

    st.dataframe(cat_disp.style.map(colour_cat_var,subset=["Variance (days)"]).format({
        "DIO (days)":"{:.1f}","Target (days)":"{:.1f}","Variance (days)":"{:+.1f}",
        "Weeks Cover":"{:.1f}","Total Inv. Value (£)":"£{:,.0f}","Est. Excess (£)":"£{:,.0f}"
    }), use_container_width=True, height=340)

    st.caption(f"Excess value = estimated cash tied up above the DIO target for each category in {sel_store2}.")

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — SKU REPLENISHMENT ACTIONS
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🔬 SKU-Level Replenishment Recommendations")
    st.caption("Identify the specific products driving excess DIO and the recommended action for each.")

    s1, s2, s3 = st.columns(3)
    with s1:
        sel_store3  = st.selectbox("Select Store", store_df.sort_values("dio_variance",ascending=False)["store_name"].values, key="t3_store")
    with s2:
        sel_cat3    = st.selectbox("Select Category", ["All Categories"] + CATEGORIES, key="t3_cat")
    with s3:
        sel_action3 = st.selectbox("Filter by Recommended Action",
                                   ["All Actions"] + REPLEN_ACTIONS, key="t3_action")

    store_id3  = store_df[store_df["store_name"]==sel_store3]["store_id"].values[0]
    sku_subset = sku_df[sku_df["store_id"]==store_id3].copy()
    if sel_cat3 != "All Categories":
        sku_subset = sku_subset[sku_subset["category"]==sel_cat3]
    if sel_action3 != "All Actions":
        sku_subset = sku_subset[sku_subset["recommended_action"]==sel_action3]

    sku_subset = sku_subset.sort_values("sku_variance", ascending=False)

    # Summary insight
    total_excess_sku = sku_subset["excess_value_gbp"].sum()
    top_sku = sku_subset.iloc[0] if len(sku_subset) > 0 else None

    if top_sku is not None:
        st.markdown(
            f"<div class='insight-card'>🔍 <b>Top offender:</b> <b>{top_sku['sku_name']}</b> "
            f"({top_sku['category']}) has a DIO variance of <b>+{top_sku['sku_variance']:.1f} days</b> "
            f"with an estimated <b>£{top_sku['excess_value_gbp']:,.0f}</b> tied up in excess stock.<br>"
            f"Recommended action: <b>{top_sku['recommended_action']}</b></div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div class='action-card'>💰 Total estimated excess value across <b>{len(sku_subset)} SKUs</b> "
            f"shown: <b>£{total_excess_sku:,.0f}</b></div>",
            unsafe_allow_html=True
        )

    # Charts
    ch1, ch2 = st.columns([1.3, 1])

    with ch1:
        st.subheader("Top 10 SKUs by DIO Variance")
        top10 = sku_subset.head(10)
        color_map2 = {"Markdown & Clear": TESCO_RED, "Reduce Order Qty": AMBER,
                      "Increase Frequency": TESCO_BLUE, "Transfer to Another Store": GREY,
                      "Review Par Level": GREEN}
        fig_sku = px.bar(
            top10.sort_values("sku_variance"),
            x="sku_variance", y="sku_name",
            color="recommended_action", orientation="h",
            color_discrete_map=color_map2,
            labels={"sku_variance":"DIO Variance (days)","sku_name":"SKU","recommended_action":"Recommended Action"},
        )
        fig_sku.update_layout(height=380, margin=dict(t=10,b=10), legend=dict(orientation="h",yanchor="bottom",y=-0.45))
        st.plotly_chart(fig_sku, use_container_width=True)

    with ch2:
        st.subheader("Actions Required — SKU Count")
        action_counts = sku_subset["recommended_action"].value_counts().reset_index()
        action_counts.columns = ["Action","Count"]
        fig_act = px.pie(action_counts, names="Action", values="Count", hole=0.45,
                         color="Action", color_discrete_map=color_map2)
        fig_act.update_layout(height=380, margin=dict(t=10,b=10))
        st.plotly_chart(fig_act, use_container_width=True)

    # SKU detail table
    st.markdown("---")
    st.subheader("SKU Action Table")
    st.caption("Every row is a specific product decision. Sort by Excess Value to prioritise cash release.")

    sku_disp = sku_subset[[
        "category","sku_name","sku_dio","sku_target","sku_variance",
        "stock_units","daily_sales_units","weeks_cover","excess_units","excess_value_gbp","recommended_action"
    ]].rename(columns={
        "category":"Category","sku_name":"SKU","sku_dio":"DIO (days)",
        "sku_target":"Target (days)","sku_variance":"Variance (days)",
        "stock_units":"Stock (units)","daily_sales_units":"Daily Sales",
        "weeks_cover":"Weeks Cover","excess_units":"Excess Units",
        "excess_value_gbp":"Excess Value (£)","recommended_action":"Recommended Action"
    }).reset_index(drop=True)

    def colour_action(v):
        cm = {"Markdown & Clear":      f"background-color:#FBE7E6;color:{TESCO_RED};font-weight:bold;",
              "Reduce Order Qty":       f"background-color:#FCF3E5;color:{AMBER};font-weight:bold;",
              "Increase Frequency":     f"background-color:#EAF1F8;color:{TESCO_BLUE};font-weight:bold;",
              "Transfer to Another Store":f"background-color:#ECECEC;color:{GREY};font-weight:bold;",
              "Review Par Level":       f"background-color:#EFF6F1;color:{GREEN};font-weight:bold;"}
        return cm.get(v,"")

    def colour_sku_var(v):
        if v>10:  return f"color:{TESCO_RED};font-weight:bold;"
        elif v>5: return f"color:{AMBER};font-weight:bold;"
        elif v>2: return f"color:{TESCO_BLUE};"
        return f"color:{GREEN};"

    styled_sku = (sku_disp.style
                  .map(colour_sku_var, subset=["Variance (days)"])
                  .map(colour_action,  subset=["Recommended Action"])
                  .format({"DIO (days)":"{:.1f}","Target (days)":"{:.1f}",
                           "Variance (days)":"{:+.1f}","Daily Sales":"{:.1f}",
                           "Weeks Cover":"{:.1f}","Excess Value (£)":"£{:,.0f}"}))

    st.dataframe(styled_sku, use_container_width=True, height=480)

    st.markdown("---")
    st.caption("Tesco | AI & Advanced Analytics for Working Capital Optimisation — Store DIO Scorecard (Demo Data)")
