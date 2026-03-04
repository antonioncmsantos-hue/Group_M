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
# Ensure the project root is on sys.path so that the local ⁠ okavango ⁠ package
# can be imported regardless of the working directory from which Streamlit is
# launched.
PROJECT_ROOT = Path(_file_).resolve().parents[1]
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


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

@st.cache_resource
def load_data() -> OkavangoData:
    """Load and cache the Okavango dataset manager.

    Uses Streamlit's `⁠ cache_resource ⁠` decorator so that data is downloaded
    and merged only once per session, rather than on every user interaction.

    Returns
    -------
    OkavangoData
        An initialised instance containing all merged GeoDataFrames as
        attributes, ready for plotting and analysis.
    """
    return OkavangoData(OkavangoConfig())


data = load_data()


# ---------------------------------------------------------------------------
# Dataset Selection
# ---------------------------------------------------------------------------

# Let the user choose which environmental dataset to visualise.
# The keys of ⁠ merged_maps ⁠ correspond to human-readable dataset names.
dataset_name = st.selectbox("Select dataset", list(data.merged_maps.keys()))
gdf = data.merged_maps[dataset_name].copy()

# Display available columns to help with debugging and exploration.
st.write("Columns:", list(gdf.columns))

# ---------------------------------------------------------------------------
# Value Column Preparation
# ---------------------------------------------------------------------------

# After merging CSVs with the GeoDataFrame, the numeric column of interest is
# standardised to "value" (set during the merge step in data_manager.py).
value_column = "value"

# Coerce to numeric: the merge can introduce strings or NaN for countries
# with no matching data row; pd.to_numeric with errors="coerce" converts
# those to NaN, which matplotlib handles gracefully as missing data.
gdf[value_column] = pd.to_numeric(gdf[value_column], errors="coerce")

# ---------------------------------------------------------------------------
# Most Recent Year (Dynamic — Not Hardcoded)
# ---------------------------------------------------------------------------

# Identify the latest year present in the dataset so the caption always
# reflects the actual data, even as the source CSVs are updated over time.
latest_year = int(gdf["Year"].dropna().max()) if gdf["Year"].notna().any() else None
if latest_year is not None:
    st.caption(f"Latest year in dataset: {latest_year}")


# ---------------------------------------------------------------------------
# World Map
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 6))

# Plot the choropleth map; countries with no data are shown in light grey
# so they are visually distinguishable from countries with a value of zero.
gdf.plot(
    column=value_column,
    ax=ax,
    legend=True,
    missing_kwds={"color": "lightgrey"},
)

ax.set_title(dataset_name)
ax.axis("off")  # Remove axis ticks/labels — not meaningful on a world map.
st.pyplot(fig)


# ---------------------------------------------------------------------------
# Top 5 and Bottom 5 Countries
# ---------------------------------------------------------------------------

st.subheader("Top 5 and Bottom 5 Countries")

# Drop rows with missing values before sorting to avoid NaN propagation.
df_sorted = gdf.dropna(subset=[value_column]).sort_values(value_column)

# Lowest-value countries (e.g. most deforested) appear at the head after
# an ascending sort; highest-value countries appear at the tail.
bottom5 = df_sorted.head(5)[["ADMIN", value_column]].reset_index(drop=True)
top5 = df_sorted.tail(5)[["ADMIN", value_column]].reset_index(drop=True)

col1, col2 = st.columns(2)

with col1:
    st.write("Bottom 5")
    st.dataframe(bottom5, use_container_width=True)

with col2:
    st.write("Top 5")
    st.dataframe(top5, use_container_width=True)


# ---------------------------------------------------------------------------
# Horizontal Bar Chart — Top 5 vs Bottom 5
# ---------------------------------------------------------------------------

# Combine both groups into a single DataFrame for a unified chart.
# The "group" column is added for potential future colour-coding by group.
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

# Invert y-axis so the country with the highest value appears at the top,
# which is the conventional reading direction for ranked bar charts.
ax2.invert_yaxis()

st.pyplot(fig2)