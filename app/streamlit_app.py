from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from okavango.data_manager import OkavangoData, OkavangoConfig


st.set_page_config(layout="wide")
st.title("🌍 Project Okavango")


@st.cache_resource
def load_data() -> OkavangoData:
    return OkavangoData(OkavangoConfig())


data = load_data()

dataset_name = st.selectbox("Select dataset", list(data.merged_maps.keys()))
gdf = data.merged_maps[dataset_name].copy()
st.write("Columns:", list(gdf.columns))

# Coluna padrão de valor (definida no merge_world_with_dataset via rename -> "value")
value_column = "value"
gdf[value_column] = pd.to_numeric(gdf[value_column], errors="coerce")

# Ano mais recente disponível (não hardcoded)
latest_year = int(gdf["Year"].dropna().max()) if gdf["Year"].notna().any() else None
if latest_year is not None:
    st.caption(f"Latest year in dataset: {latest_year}")

# --- MAPA ---
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

# --- TOP/BOTTOM 5 ---
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

# --- GRÁFICO (bar chart) ---
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