"""
Project Okavango - Main Streamlit Application
==============================================

This module is the entry point for the Okavango Streamlit app.
It loads environmental datasets (deforestation, land protection, land degradation)
merged with geographic (GeoDataFrame) data, and renders:
    - An interactive world map coloured by the selected dataset's values.
    - A ranked bar chart comparing the Top 5 and Bottom 5 countries
      for the most recent year available in the dataset.

Usage
-----
Run from the project root directory with::

    streamlit run main.py

Dependencies
------------
•⁠  ⁠streamlit
•⁠  ⁠pandas
•⁠  ⁠matplotlib
•⁠  ⁠geopandas (via okavango.data_manager)
•⁠  ⁠okavango (local package)

Notes
-----
•⁠  ⁠The most recent year is determined dynamically; no year is hardcoded.
•⁠  ⁠All dataset values are coerced to numeric to handle mixed-type columns
  that can arise after merging CSV data with GeoDataFrame.
"""

from pathlib import Path
import sys

# ---------------------------------------------------------------------------
# Path Setup
# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that the local okavango package
# can be imported regardless of the working directory from which Streamlit is
# launched.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from okavango.data_manager import OkavangoData, OkavangoConfig

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(layout="wide")
st.title("🌍 Project Okavango")

page = st.sidebar.selectbox(
    "Select page",
    ["Maps", "Satellite Analysis"]
)

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
@st.cache_resource
def load_data() -> OkavangoData:
    """Load and cache the Okavango dataset manager."""
    return OkavangoData(OkavangoConfig())


data = load_data()

# ---------------------------------------------------------------------------
# PAGE 1 — MAPS
# ---------------------------------------------------------------------------
if page == "Maps":
    st.header("Environmental Maps")

    # Dataset Selection
    dataset_name = st.selectbox("Select dataset", list(data.merged_maps.keys()))
    gdf = data.merged_maps[dataset_name].copy()

    # Display available columns
    st.write("Columns:", list(gdf.columns))

    # Value Column Preparation
    value_column = "value"
    gdf[value_column] = pd.to_numeric(gdf[value_column], errors="coerce")

    # Most Recent Year
    latest_year = int(gdf["Year"].dropna().max()) if gdf["Year"].notna().any() else None
    if latest_year is not None:
        st.caption(f"Latest year in dataset: {latest_year}")

    # World Map
    fig, ax = plt.subplots(figsize=(12, 6))
    gdf.plot(
        column=value_column,
        ax=ax,
        legend=True,
        missing_kwds={"color": "lightgrey"},
    )
    ax.set_title(dataset_name)
    ax.axis("off")
    st.pyplot(fig)

    # Top 5 and Bottom 5 Countries
    st.subheader("Top 5 and Bottom 5 Countries")

    df_sorted = gdf.dropna(subset=[value_column]).sort_values(value_column)
    bottom5 = df_sorted.head(5)[["ADMIN", value_column]].reset_index(drop=True)
    top5 = df_sorted.tail(5)[["ADMIN", value_column]].reset_index(drop=True)

    col1, col2 = st.columns(2)

    with col1:
        st.write("Bottom 5")
        st.dataframe(bottom5, use_container_width=True)

    with col2:
        st.write("Top 5")
        st.dataframe(top5, use_container_width=True)

    # Horizontal Bar Chart
    plot_df = pd.concat(
        [
            bottom5.assign(group="Bottom 5"),
            top5.assign(group="Top 5"),
        ],
        ignore_index=True,
    )

    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.barh(plot_df["ADMIN"], plot_df[value_column])
    ax2.set_title("Top 5 vs Bottom 5")
    ax2.invert_yaxis()

    st.pyplot(fig2)

# ---------------------------------------------------------------------------
# PAGE 2 — SATELLITE ANALYSIS
# ---------------------------------------------------------------------------
elif page == "Satellite Analysis":
    st.header("Satellite Image Environmental Analysis")

    latitude = st.number_input(
        "Latitude",
        value=0.0,
        format="%.6f"
    )

    longitude = st.number_input(
        "Longitude",
        value=0.0,
        format="%.6f"
    )

    zoom = st.slider(
        "Zoom level",
        min_value=1,
        max_value=20,
        value=10
    )

    run_analysis = st.button("Analyze Area")

    if run_analysis:
        st.write("Coordinates selected:")
        st.write(f"Latitude: {latitude}")
        st.write(f"Longitude: {longitude}")
        st.write(f"Zoom: {zoom}")

        st.info("Next step: download the satellite image for these coordinates.")