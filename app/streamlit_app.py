"""
Project Okavango - Main Streamlit Application
=============================================

This module is the main Streamlit application for Project Okavango.
It provides:

- Page 1: environmental maps based on merged OWID + Natural Earth data
- Page 2: satellite image download and environmental risk analysis with Ollama
"""

from datetime import datetime
from pathlib import Path
import json
import math
import subprocess
import sys

# Path setup must come before local package imports so the local project
# package can be imported correctly when Streamlit runs the app.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import ollama
import pandas as pd
import requests
import streamlit as st
import yaml
from PIL import Image

from okavango.data_manager import OkavangoConfig, OkavangoData


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Directory where downloaded satellite images are stored locally.
IMAGES_DIR = PROJECT_ROOT / "images"
IMAGES_DIR.mkdir(exist_ok=True)

# CSV file used as a lightweight database for storing previous analyses.
DB_PATH = PROJECT_ROOT / "database" / "images.csv"

# ESRI endpoint used to export static satellite imagery for a chosen area.
ESRI_WORLD_IMAGERY_EXPORT_URL = (
    "https://services.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/export"
)

# Expected schema of the image analysis database CSV.
IMAGE_DB_COLUMNS = [
    "timestamp",
    "latitude",
    "longitude",
    "zoom",
    "image_path",
    "image_description",
    "image_prompt",
    "image_model",
    "text_assessment",
    "text_prompt",
    "text_model",
    "danger",
]

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Project Okavango")
st.title("🌍 Project Okavango")

page = st.sidebar.selectbox(
    "Select page",
    ["Maps", "Satellite Analysis"],
)

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------
def build_image_path(latitude: float, longitude: float, zoom: int) -> Path:
    """
    Build a deterministic file path for a satellite image.

    The filename is generated from latitude, longitude, and zoom so that the
    same request always maps to the same local image file.

    Parameters
    ----------
    latitude : float
        Latitude of the selected area.
    longitude : float
        Longitude of the selected area.
    zoom : int
        Zoom level used to capture the satellite image.

    Returns
    -------
    Path
        Full path where the satellite image should be stored.

    Notes
    -----
    Special characters are replaced to keep filenames safe and consistent
    across operating systems.
    """
    safe_lat = f"{latitude:.6f}".replace("-", "m").replace(".", "_")
    safe_lon = f"{longitude:.6f}".replace("-", "m").replace(".", "_")
    filename = f"img_lat_{safe_lat}_lon_{safe_lon}_zoom_{zoom}.png"
    return IMAGES_DIR / filename


def latlon_to_web_mercator(latitude: float, longitude: float) -> tuple[float, float]:
    """
    Convert geographic coordinates to Web Mercator coordinates.

    This function converts latitude and longitude from EPSG:4326 to the
    Web Mercator projection EPSG:3857, which is required by the ESRI
    satellite imagery service.

    Parameters
    ----------
    latitude : float
        Latitude in decimal degrees.
    longitude : float
        Longitude in decimal degrees.

    Returns
    -------
    tuple[float, float]
        Projected ``(x, y)`` coordinates in Web Mercator.

    Notes
    -----
    Latitude is clamped to the valid Web Mercator range to avoid invalid
    projection values near the poles.
    """
    origin_shift = 20037508.34
    x = longitude * origin_shift / 180.0

    clamped_lat = max(min(latitude, 85.05112878), -85.05112878)
    y = math.log(math.tan((90.0 + clamped_lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * origin_shift / 180.0

    return x, y


def build_bbox_web_mercator(
    latitude: float,
    longitude: float,
    zoom: int,
    width: int = 640,
    height: int = 640,
) -> tuple[float, float, float, float]:
    """
    Build a Web Mercator bounding box around a selected location.

    The bounding box is derived from the selected center point, zoom level,
    and requested image dimensions. It is used as input for the ESRI export
    service.

    Parameters
    ----------
    latitude : float
        Latitude of the center point.
    longitude : float
        Longitude of the center point.
    zoom : int
        Zoom level controlling the spatial scale of the exported image.
    width : int, optional
        Output image width in pixels, by default 640.
    height : int, optional
        Output image height in pixels, by default 640.

    Returns
    -------
    tuple[float, float, float, float]
        Bounding box in the form ``(xmin, ymin, xmax, ymax)`` in EPSG:3857.
    """
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
    """
    Download a satellite image for a selected area from ESRI World Imagery.

    Parameters
    ----------
    latitude : float
        Latitude of the selected center point.
    longitude : float
        Longitude of the selected center point.
    zoom : int
        Zoom level used to define the spatial extent of the image.
    output_path : Path
        Local path where the downloaded image will be stored.
    width : int, optional
        Output image width in pixels, by default 640.
    height : int, optional
        Output image height in pixels, by default 640.

    Returns
    -------
    Path
        Path to the saved image file.

    Raises
    ------
    requests.HTTPError
        Raised if the ESRI request fails or returns an unsuccessful status code.

    Notes
    -----
    The export request uses a Web Mercator bounding box and returns a static
    raster image for the requested area.
    """
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
    """
    Ensure that a required Ollama model is available locally.

    The function checks whether the specified model is already installed.
    If not, it triggers an ``ollama pull`` command.

    Parameters
    ----------
    model_name : str
        Name of the Ollama model required by the application.

    Raises
    ------
    RuntimeError
        Raised if Ollama is not installed or cannot be found in the system PATH.
    subprocess.CalledProcessError
        Raised if the model listing or pulling command fails.
    """
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

    # Pull the model only if it is not already available locally.
    if model_name not in result.stdout:
        subprocess.run(
            ["ollama", "pull", model_name],
            check=True,
        )


def describe_image_with_ollama(
    image_path: Path,
    model_name: str,
    prompt: str,
) -> str:
    """
    Generate a textual description of a satellite image using an Ollama vision model.

    Parameters
    ----------
    image_path : Path
        Path to the local satellite image file.
    model_name : str
        Name of the Ollama vision-capable model to use.
    prompt : str
        Prompt instructing the model how to describe the image.

    Returns
    -------
    str
        Textual description generated by the model.

    Notes
    -----
    The image is passed to the model through the Ollama chat API together
    with the provided prompt.
    """
    ensure_ollama_model(model_name)

    response = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [str(image_path)],
            }
        ],
    )

    return response["message"]["content"]


def assess_environmental_risk_with_ollama(
    image_description: str,
    model_name: str,
    prompt: str,
) -> str:
    """
    Assess environmental risk from a generated image description using Ollama.

    Parameters
    ----------
    image_description : str
        Textual description of the satellite image.
    model_name : str
        Name of the Ollama text model used for the risk assessment.
    prompt : str
        Prompt instructing the model how to analyse environmental risk.

    Returns
    -------
    str
        Raw text response returned by the model, expected to contain a JSON-like
        risk assessment structure.
    """
    ensure_ollama_model(model_name)

    # Combine the task prompt with the previously generated image description.
    full_prompt = f"{prompt}\n\nSatellite image description:\n{image_description}"

    response = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": full_prompt,
            }
        ],
    )

    return response["message"]["content"]


def parse_risk_response(risk_response: str) -> dict[str, object]:
    """
    Parse the model response from the environmental risk assessment step.

    Parameters
    ----------
    risk_response : str
        Raw text returned by the risk assessment model.

    Returns
    -------
    dict[str, object]
        Dictionary containing the parsed fields:
        ``danger``, ``confidence``, ``summary``, and ``reasons``.

    Notes
    -----
    If the model response is not valid JSON, the function falls back to a
    default structure and stores the raw response inside the summary field.
    """
    try:
        parsed = json.loads(risk_response)
        return {
            "danger": parsed.get("danger", "UNKNOWN"),
            "confidence": parsed.get("confidence", "Unknown"),
            "summary": parsed.get("summary", ""),
            "reasons": parsed.get("reasons", []),
        }
    except json.JSONDecodeError:
        return {
            "danger": "UNKNOWN",
            "confidence": "Unknown",
            "summary": risk_response,
            "reasons": [],
        }


def display_risk_status(danger_flag: str, confidence: str) -> None:
    """
    Display a visual status message for the environmental risk result.

    Parameters
    ----------
    danger_flag : str
        Risk flag returned by the model, typically ``Yes``, ``No``, or ``UNKNOWN``.
    confidence : str
        Confidence level associated with the risk prediction.
    """
    if danger_flag == "Yes":
        if confidence == "High":
            st.error("⚠️ Area flagged as being at environmental risk.")
        else:
            st.warning("⚠️ Area possibly flagged as being at environmental risk.")
    elif danger_flag == "No":
        if confidence == "High":
            st.success("✅ Area not flagged as being at environmental risk.")
        else:
            st.info("ℹ️ No clear environmental risk detected, but confidence is limited.")
    else:
        st.warning("❓ Risk status could not be determined clearly.")


def load_model_config(config_path: Path = PROJECT_ROOT / "models.yaml") -> dict:
    """
    Load model configuration and prompts from a YAML file.

    Parameters
    ----------
    config_path : Path, optional
        Path to the YAML configuration file, by default
        ``PROJECT_ROOT / "models.yaml"``.

    Returns
    -------
    dict
        Parsed configuration dictionary containing model names, prompts,
        and image settings.
    """
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_image_database(db_path: Path = DB_PATH) -> pd.DataFrame:
    """
    Load the CSV database of previously analysed satellite images.

    Parameters
    ----------
    db_path : Path, optional
        Path to the CSV database file, by default ``DB_PATH``.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the stored analyses. If the database file does
        not exist or is empty, an empty DataFrame with the expected schema
        is returned.
    """
    if not db_path.exists() or db_path.stat().st_size == 0:
        return pd.DataFrame(columns=IMAGE_DB_COLUMNS)

    return pd.read_csv(db_path)


def find_existing_analysis(
    latitude: float,
    longitude: float,
    zoom: int,
    db_path: Path = DB_PATH,
) -> pd.Series | None:
    """
    Find a previously stored analysis for the same location and zoom level.

    Parameters
    ----------
    latitude : float
        Latitude used in the current request.
    longitude : float
        Longitude used in the current request.
    zoom : int
        Zoom level used in the current request.
    db_path : Path, optional
        Path to the CSV database file, by default ``DB_PATH``.

    Returns
    -------
    pandas.Series | None
        The most recent matching analysis row if one exists, otherwise ``None``.

    Notes
    -----
    Matching is based on exact equality of latitude, longitude, and zoom.
    """
    df = load_image_database(db_path)

    if df.empty:
        return None

    matches = df[
        (df["latitude"] == latitude)
        & (df["longitude"] == longitude)
        & (df["zoom"] == zoom)
    ]

    if matches.empty:
        return None

    return matches.iloc[-1]


def append_analysis_to_database(
    latitude: float,
    longitude: float,
    zoom: int,
    image_path: Path,
    image_description: str,
    image_prompt: str,
    image_model: str,
    text_assessment: str,
    text_prompt: str,
    text_model: str,
    danger: str,
    db_path: Path = DB_PATH,
) -> None:
    """
    Append a new satellite image analysis result to the CSV database.

    Parameters
    ----------
    latitude : float
        Latitude of the analysed area.
    longitude : float
        Longitude of the analysed area.
    zoom : int
        Zoom level used for the satellite image.
    image_path : Path
        Path to the stored satellite image.
    image_description : str
        Description generated by the image analysis model.
    image_prompt : str
        Prompt used for image description generation.
    image_model : str
        Name of the image analysis model.
    text_assessment : str
        Raw environmental risk assessment output.
    text_prompt : str
        Prompt used for the risk assessment model.
    text_model : str
        Name of the risk assessment model.
    danger : str
        Final danger flag stored in the database.
    db_path : Path, optional
        Path to the CSV database file, by default ``DB_PATH``.

    Returns
    -------
    None
        This function writes data to disk and does not return a value.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the new record as a one-row DataFrame for easy CSV appending.
    new_row = pd.DataFrame(
        [
            {
                "timestamp": datetime.now().isoformat(),
                "latitude": latitude,
                "longitude": longitude,
                "zoom": zoom,
                "image_path": str(image_path),
                "image_description": image_description,
                "image_prompt": image_prompt,
                "image_model": image_model,
                "text_assessment": text_assessment,
                "text_prompt": text_prompt,
                "text_model": text_model,
                "danger": danger,
            }
        ]
    )

    file_exists = db_path.exists() and db_path.stat().st_size > 0
    new_row.to_csv(db_path, mode="a", header=not file_exists, index=False)


def render_risk_results(parsed_risk: dict[str, object]) -> None:
    """
    Render the parsed environmental risk result in the Streamlit interface.

    Parameters
    ----------
    parsed_risk : dict[str, object]
        Dictionary containing the parsed risk assessment output.

    Returns
    -------
    None
        This function only updates the Streamlit interface.
    """
    st.subheader("Environmental Risk Assessment")
    st.write(f"**Danger:** {parsed_risk['danger']}")
    st.write(f"**Confidence:** {parsed_risk['confidence']}")
    st.write(f"**Summary:** {parsed_risk['summary']}")

    reasons = parsed_risk.get("reasons", [])
    if reasons:
        st.write("**Reasons:**")
        for reason in reasons:
            st.markdown(f"- {reason}")

    display_risk_status(
        str(parsed_risk["danger"]),
        str(parsed_risk["confidence"]),
    )


@st.cache_resource
def load_data() -> OkavangoData:
    """
    Load and cache the main Okavango data manager instance.

    Returns
    -------
    OkavangoData
        Cached instance containing downloaded, loaded, and merged datasets.

    Notes
    -----
    Streamlit caches this resource to avoid repeating expensive download and
    loading operations on every rerun.
    """
    return OkavangoData(OkavangoConfig())


# Load the environmental datasets and model configuration once at app startup.
data = load_data()
model_config = load_model_config()

# ---------------------------------------------------------------------------
# PAGE 1 — MAPS
# ---------------------------------------------------------------------------
if page == "Maps":
    st.header("Environmental Maps")

    # Let the user select which environmental indicator to display.
    dataset_name = st.selectbox("Select dataset", list(data.merged_maps.keys()))
    gdf = data.merged_maps[dataset_name].copy()

    # Standardised value column produced by the merge step.
    value_column = "value"
    gdf[value_column] = pd.to_numeric(gdf[value_column], errors="coerce")

    # Display the latest year available in the selected dataset.
    latest_year = int(gdf["Year"].dropna().max()) if gdf["Year"].notna().any() else None
    if latest_year is not None:
        st.caption(f"Latest year in dataset: {latest_year}")

    # Render the choropleth-style world map.
    fig, ax = plt.subplots(figsize=(12, 6))
    gdf.plot(
        column=value_column,
        ax=ax,
        legend=True,
        missing_kwds={"color": "lightgrey"},
    )
    ax.set_title(dataset_name.replace("_", " ").title())
    ax.axis("off")
    st.pyplot(fig)

    st.subheader("Top 5 and Bottom 5 Countries")

    # Sort countries by indicator value to extract the top and bottom performers.
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

    # Combine both groups into a single dataset for the comparison bar chart.
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
        format="%.6f",
    )

    longitude = st.number_input(
        "Longitude",
        value=0.0,
        format="%.6f",
    )

    zoom = st.slider(
        "Zoom level",
        min_value=1,
        max_value=20,
        value=10,
    )

    run_analysis = st.button("Analyze Area")

    # Read model names, prompts, and output image settings from the YAML config.
    image_model = model_config["image_analysis"]["model"]
    image_prompt = model_config["image_analysis"]["prompt"]

    risk_model = model_config["risk_analysis"]["model"]
    risk_prompt = model_config["risk_analysis"]["prompt"]

    image_width = model_config["image_settings"]["width"]
    image_height = model_config["image_settings"]["height"]

    if run_analysis:
        image_path = build_image_path(latitude, longitude, zoom)

        # Check whether the same analysis was already performed before.
        existing_result = find_existing_analysis(
            latitude=latitude,
            longitude=longitude,
            zoom=zoom,
        )

        if existing_result is not None:
            st.success("Analysis already exists in the database. Reusing stored result.")

            existing_image_path = Path(existing_result["image_path"])
            if existing_image_path.exists():
                image = Image.open(existing_image_path)
                st.image(image, caption="Satellite image", use_container_width=True)

            st.subheader("Image Description")
            st.write(existing_result["image_description"])

            parsed_risk = parse_risk_response(existing_result["text_assessment"])
            render_risk_results(parsed_risk)
            st.stop()

        # Download the image only if it is not already stored locally.
        if not image_path.exists():
            try:
                with st.spinner("Downloading satellite image..."):
                    download_satellite_image(
                        latitude=latitude,
                        longitude=longitude,
                        zoom=zoom,
                        output_path=image_path,
                        width=image_width,
                        height=image_height,
                    )
                st.success("Satellite image downloaded successfully.")
            except Exception as error:
                st.error(f"Failed to download image: {error}")
                st.stop()

        try:
            image = Image.open(image_path)
            st.image(image, caption="Satellite image", use_container_width=True)

            with st.spinner("Generating image description with Ollama..."):
                image_description = describe_image_with_ollama(
                    image_path=image_path,
                    model_name=image_model,
                    prompt=image_prompt,
                )

            st.subheader("Image Description")
            st.write(image_description)

            with st.spinner("Assessing environmental risk..."):
                risk_response = assess_environmental_risk_with_ollama(
                    image_description=image_description,
                    model_name=risk_model,
                    prompt=risk_prompt,
                )

            parsed_risk = parse_risk_response(risk_response)
            render_risk_results(parsed_risk)

            # Save the newly generated result so repeated analyses can be reused.
            append_analysis_to_database(
                latitude=latitude,
                longitude=longitude,
                zoom=zoom,
                image_path=image_path,
                image_description=image_description,
                image_prompt=image_prompt,
                image_model=image_model,
                text_assessment=risk_response,
                text_prompt=risk_prompt,
                text_model=risk_model,
                danger=str(parsed_risk["danger"]),
            )

        except Exception as error:
            st.error(f"Failed to open image or run AI pipeline: {error}")