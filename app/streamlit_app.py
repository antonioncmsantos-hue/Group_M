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
import math
import requests
import ollama
import subprocess
from PIL import Image

from okavango.data_manager import OkavangoData, OkavangoConfig

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(layout="wide")
st.title("🌍 Project Okavango")

IMAGES_DIR = PROJECT_ROOT / "images"
IMAGES_DIR.mkdir(exist_ok=True)

ESRI_WORLD_IMAGERY_EXPORT_URL = (
    "https://services.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/export"
)

page = st.sidebar.selectbox(
    "Select page",
    ["Maps", "Satellite Analysis"]
)

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def build_image_path(latitude: float, longitude: float, zoom: int) -> Path:
    """Create a stable image file path from coordinates and zoom."""
    safe_lat = f"{latitude:.6f}".replace("-", "m").replace(".", "_")
    safe_lon = f"{longitude:.6f}".replace("-", "m").replace(".", "_")
    filename = f"img_lat_{safe_lat}_lon_{safe_lon}_zoom_{zoom}.png"
    return IMAGES_DIR / filename

def latlon_to_web_mercator(latitude: float, longitude: float) -> tuple[float, float]:
    """Convert latitude/longitude (EPSG:4326) to Web Mercator (EPSG:3857)."""
    origin_shift = 20037508.34
    x = longitude * origin_shift / 180.0

    lat = max(min(latitude, 85.05112878), -85.05112878)
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * origin_shift / 180.0

    return x, y


def build_bbox_web_mercator(
    latitude: float,
    longitude: float,
    zoom: int,
    width: int = 640,
    height: int = 640,
) -> tuple[float, float, float, float]:
    """Build a bbox around the selected point using a simple zoom-based scale."""
    center_x, center_y = latlon_to_web_mercator(latitude, longitude)

    initial_resolution = 156543.03392804097
    resolution = initial_resolution / (2 ** zoom)

    half_width_m = (width * resolution) / 2
    half_height_m = (height * resolution) / 2

    xmin = center_x - half_width_m
    ymin = center_y - half_height_m
    xmax = center_x + half_width_m
    ymax = center_y + half_height_m

    return xmin, ymin, xmax, ymax


def download_satellite_image(
    latitude: float,
    longitude: float,
    zoom: int,
    output_path: Path,
    width: int = 640,
    height: int = 640,
) -> Path:
    """Download a satellite image from ESRI World Imagery."""
    xmin, ymin, xmax, ymax = build_bbox_web_mercator(
        latitude=latitude,
        longitude=longitude,
        zoom=zoom,
        width=width,
        height=height,
    )

    params = {
        "bbox": f"{xmin},{ymin},{xmax},{ymax}",
        "bboxSR": 3857,
        "imageSR": 3857,
        "size": f"{width},{height}",
        "format": "jpg",
        "f": "image",
    }

    response = requests.get(
        ESRI_WORLD_IMAGERY_EXPORT_URL,
        params=params,
        timeout=60,
    )
    response.raise_for_status()

    output_path.write_bytes(response.content)
    return output_path

def ensure_ollama_model(model_name: str) -> None:
    """Pull the Ollama model if it does not exist locally."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "Ollama is not installed or not available in PATH."
        ) from error

    if model_name not in result.stdout:
        subprocess.run(
            ["ollama", "pull", model_name],
            check=True,
        )


def describe_image_with_ollama(
    image_path: Path,
    model_name: str = "llava:7b",
) -> str:
    """Generate an image description using an Ollama vision model."""
    ensure_ollama_model(model_name)

    response = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": (
                    "Describe this satellite image. Focus on vegetation, water, "
                    "roads, bare soil, urban expansion, mining, fire scars, "
                    "erosion, and signs of deforestation."
                ),
                "images": [str(image_path)],
            }
        ],
    )

    return response["message"]["content"]


def assess_environmental_risk_with_ollama(
    image_description: str,
    model_name: str = "llama3.2:3b",
) -> str:
    """Assess environmental risk from an image description using an Ollama text model."""
    ensure_ollama_model(model_name)

    prompt = f"""
You are an environmental risk analyst.

Given the following satellite image description, assess whether the area appears to be at environmental risk.

Check for possible signs of:
- deforestation
- land degradation
- erosion
- mining activity
- wildfire damage
- flooding
- drought
- water stress
- urban encroachment into natural areas
- habitat destruction

Image description:
{image_description}

Reply in exactly this format:

Danger: Y or N
Confidence: Low, Medium, or High
Reasons:
- reason 1
- reason 2
- reason 3
"""

    response = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response["message"]["content"]


def extract_danger_flag(risk_response: str) -> str:
    """Extract the danger flag from the model response."""
    response_upper = risk_response.upper()

    if "DANGER: Y" in response_upper:
        return "Y"
    if "DANGER: N" in response_upper:
        return "N"

    return "UNKNOWN"


def display_risk_status(danger_flag: str) -> None:
    """Display a visual risk indicator in Streamlit."""
    if danger_flag == "Y":
        st.error("⚠️ Area flagged as being at environmental risk.")
    elif danger_flag == "N":
        st.success("✅ Area not flagged as being at environmental risk.")
    else:
        st.warning("❓ Risk status could not be determined clearly.")



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

        image_path = build_image_path(latitude, longitude, zoom)

        st.write("Image will be saved as:")
        st.code(str(image_path))

        if image_path.exists():
            st.success("This image already exists. No need to download it again.")
        else:
            st.warning("This image does not exist yet. Downloading now...")

            try:
                download_satellite_image(
                    latitude=latitude,
                    longitude=longitude,
                    zoom=zoom,
                    output_path=image_path,
                    width=640,
                    height=640,
                )
                st.success("Satellite image downloaded successfully.")
            except Exception as error:
                st.error(f"Failed to download image: {error}")

        if image_path.exists():
            try:
                image = Image.open(image_path)
                st.image(image, caption="Satellite image", use_container_width=True)

                st.info("Generating image description with Ollama...")

                image_description = describe_image_with_ollama(
                    image_path,
                    model_name="llava:7b"
                )

                st.subheader("Image Description")
                st.write(image_description)

                st.info("Assessing environmental risk...")

                risk_response = assess_environmental_risk_with_ollama(
                    image_description=image_description,
                    model_name="llama3.2:3b",
                )

                st.subheader("Environmental Risk Assessment")
                st.write(risk_response)

                danger_flag = extract_danger_flag(risk_response)
                display_risk_status(danger_flag)

            except Exception as error:
                st.error(f"Failed to open image or run AI pipeline: {error}")