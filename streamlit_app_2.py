import streamlit as st
import pandas as pd
import glob
import altair as alt

st.set_page_config(layout="wide")

# --- Load Data ---
@st.cache_data
def load_data():
    csv_files = glob.glob("*_deduped.csv")
    df_all = pd.DataFrame()
    for file in csv_files:
        df = pd.read_csv(file)
        if "Date" not in df.columns or "Rating" not in df.columns or "Brand" not in df.columns:
            continue
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce", utc=True)
        df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
        df = df.dropna(subset=["Date", "Rating"])
        df_all = pd.concat([df_all, df], ignore_index=True)
    return df_all

df_all = load_data()

# --- Sidebar Navigation ---
st.sidebar.title("📊 EmberBus Dashboard")
page = st.sidebar.radio("Choose a page", ["Monthly Ratings", "Management Dashboard"])

# --- Monthly Ratings Page ---
if page == "Monthly Ratings":
    st.title("📈 Monthly Average Trustpilot Rating per Brand")

    if df_all.empty:
        st.warning("No valid deduped CSV files found.")
    else:
        df_all["Month"] = df_all["Date"].dt.to_period("M").dt.to_timestamp()
        monthly_avg = df_all.groupby(["Brand", "Month"])["Rating"].mean().reset_index()
        pivot_df = monthly_avg.pivot(index="Month", columns="Brand", values="Rating")

        # Fill in missing months and forward fill
        full_range = pd.date_range(start=pivot_df.index.min(), end=pivot_df.index.max(), freq="MS")
        pivot_df = pivot_df.reindex(full_range).ffill()

        # Reshape for Altair
        chart_data = pivot_df.reset_index().melt(id_vars="index", var_name="Brand", value_name="AvgRating")
        chart_data = chart_data.rename(columns={"index": "Month"})

        # --- User-adjustable chart size ---
        with st.expander("🛠️ Customize Chart Size"):
            user_width = st.slider("Chart width (px)", min_value=400, max_value=1600, value=1000, step=100)
            user_height = st.slider("Chart height (px)", min_value=300, max_value=1000, value=500, step=50)

        chart = alt.Chart(chart_data).mark_line(point=True).encode(
            x=alt.X("Month:T", title="Month"),
            y=alt.Y("AvgRating:Q", title="Average Rating", scale=alt.Scale(domain=[0, 5])),
            color="Brand:N",
            tooltip=["Brand", "Month", "AvgRating"]
        ).properties(
            width=user_width,
            height=user_height,
            title="📊 Monthly Avg Trustpilot Rating per Brand"
        ).interactive()

        st.altair_chart(chart, use_container_width=False)

# --- Management Dashboard Page ---
elif page == "Management Dashboard":
    st.title("🚨 Reviews Flagged for Management")

    if "MgmtFlag" not in df_all.columns:
        st.error("MgmtFlag column not found in your CSVs. Make sure you've re-scraped Ember with the latest script.")
    else:
        flagged = df_all[df_all["MgmtFlag"] == "Yes"].copy()

        if flagged.empty:
            st.success("✅ No reviews flagged for management.")
        else:
            flagged["Date"] = pd.to_datetime(flagged["Date"], utc=True).dt.tz_localize(None)

            min_date = flagged["Date"].min().date()
            max_date = flagged["Date"].max().date()
            from_date = st.date_input("From:", min_value=min_date, max_value=max_date, value=min_date)
            to_date = st.date_input("To:", min_value=min_date, max_value=max_date, value=max_date)

            mask = (flagged["Date"] >= pd.to_datetime(from_date)) & (flagged["Date"] <= pd.to_datetime(to_date))
            filtered = flagged.loc[mask]

            st.write(f"📅 Showing {len(filtered)} flagged review(s) from {from_date} to {to_date}:")

            for _, row in filtered.iterrows():
                st.markdown(f"""
                **🟠 {row['Brand']}**  
                **Date:** {row['Date'].date()}  
                **Rating:** ⭐ {row['Rating']}  
                **Title:** {row['Title'] or 'No Title'}  
                **Review:** {row['Review'][:1000]}  
                ---
                """)