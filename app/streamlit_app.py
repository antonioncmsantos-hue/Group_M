from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import matplotlib.pyplot as plt

from okavango.data_manager import OkavangoData, OkavangoConfig


st.set_page_config(layout="wide")

st.title("🌍 Project Okavango")

@st.cache_resource
def load_data():
    return OkavangoData(OkavangoConfig())

data = load_data()

dataset_name = st.selectbox(
    "Select dataset",
    list(data.merged_maps.keys())
)

gdf = data.merged_maps[dataset_name]

value_column = [c for c in gdf.columns if c not in ["SOV_A3", "ADMIN", "geometry", "Entity", "Code", "Year"]][0]

fig, ax = plt.subplots(figsize=(12, 6))
gdf.plot(column=value_column, ax=ax, legend=True)
ax.set_title(dataset_name)
ax.axis("off")

st.pyplot(fig)

st.subheader("Top 5 and Bottom 5 Countries")

latest_year = gdf["Year"].dropna().iloc[0]

df_sorted = gdf.dropna(subset=[value_column]).sort_values(value_column)

bottom5 = df_sorted.head(5)[["ADMIN", value_column]]
top5 = df_sorted.tail(5)[["ADMIN", value_column]]

col1, col2 = st.columns(2)

with col1:
    st.write("Bottom 5")
    st.dataframe(bottom5)

with col2:
    st.write("Top 5")
    st.dataframe(top5)