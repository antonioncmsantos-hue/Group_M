# Group_M

Advanced Programming Group Project

## Group Members (emails)

- António Santos (antonioncmsantos) - [71212@novasbe.pt](mailto:71212@novasbe.pt)
- Margarida Cunha (margarida-passos-cunha) - [71119@novasbe.pt](mailto:71119@novasbe.pt)
- Miguel Sardo (miguelsardo) - [71929@novasbe.pt](mailto:71929@novasbe.pt)
- Rafaela Castro (rafaelaacastro) - [71923@novasbe.pt](mailto:71923@novasbe.pt)

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [How to Run the Project](#how-to-run-the-project)
- [Usage](#usage)
- [Environmental Danger Detection Examples](#environmental-danger-detection-examples)
- [Contribution to the UN Sustainable Development Goals (SDGs)](#contribution-to-the-un-sustainable-development-goals-sdgs)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Authors](#authors)
- [License](#license)

---

## Project Overview

Project Okavango is an interactive environmental monitoring application that combines global biodiversity and land-use data with AI-powered satellite image analysis. Named after the Okavango Delta, one of the world's most ecologically significant wetlands located in northwestern Botswana, the project aims to make environmental risk data more accessible and actionable, while giving powerful insights at a distance of few "clicks".

The application addresses a critical challenge in environmental protection: how to quickly identify areas at risk of deforestation, land degradation, mining damage, and habitat loss. By integrating authoritative datasets from Our World in Data (OWID) with real-time satellite imagery from ESRI World Imagery and locally-run AI models via Ollama, the app enables users to explore environmental indicators globally and investigate specific locations at high resolution.

The project is structured around two core modules:

1. **Environmental Maps** — Choropleth world maps visualising indicators such as forest loss, protected land coverage, and biodiversity decline across all countries.
2. **Satellite Analysis** — A geospatial tool that downloads satellite imagery for any coordinate on Earth and uses a local vision-language model to automatically detect signs of environmental danger.

---

## Features

- **Interactive world maps** visualising five environmental datasets from Our World in Data, filtered to the most recent year available for each country.
- **Top 5 / Bottom 5 country comparisons** per indicator, shown as sortable tables and horizontal bar charts.
- **Satellite image download** from ESRI World Imagery for any latitude/longitude and zoom level combination.
- **AI-powered image description** using a local Ollama vision model (LLaVA) that identifies vegetation, water bodies, roads, bare soil, mining activity, fire scars, erosion, and deforestation.
- **Automated environmental risk assessment** using a second Ollama language model (Llama 3.2) that analyses the image description and returns a structured JSON report with a danger flag, confidence level, summary, and detailed reasoning.
- **Persistent analysis database** stored as a CSV file, so previously analysed coordinates are retrieved instantly without re-running the AI pipeline.
- **Automatic Ollama model management** — required models are pulled automatically if not already installed locally.
- **Clean Streamlit interface** with a sidebar page selector, spinner feedback, and colour-coded risk status messages (success, warning, error).

---

## Tech Stack

| Category | Technology |
|---|---|
| **Frontend / UI** | [Streamlit](https://streamlit.io/) |
| **Data manipulation** | [pandas](https://pandas.pydata.org/) |
| **Geospatial data** | [GeoPandas](https://geopandas.org/), [Shapely](https://shapely.readthedocs.io/), [Fiona](https://fiona.readthedocs.io/), [pyproj](https://pyproj4.github.io/pyproj/) |
| **Mapping / Visualisation** | [Matplotlib](https://matplotlib.org/) |
| **AI inference** | [Ollama](https://ollama.com/) (LLaVA 7B for image analysis, Llama 3.2 3B for risk assessment) |
| **Satellite imagery** | [ESRI World Imagery REST API](https://services.arcgisonline.com/) |
| **HTTP requests** | [requests](https://docs.python-requests.org/) |
| **Configuration** | [PyYAML](https://pyyaml.org/) |
| **Image handling** | [Pillow](https://pillow.readthedocs.io/) |
| **Data validation** | [Pydantic](https://docs.pydantic.dev/) |
| **Testing** | [pytest](https://pytest.org/) |
| **Environmental data source** | [Our World in Data](https://ourworldindata.org/) |
| **World map geometry** | [Natural Earth](https://www.naturalearthdata.com/) (1:110m Admin 0) |

---

## Installation

### Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.com/) installed and running locally
- Git

### 1. Clone the repository

```bash
git clone https://github.com/antonioncmsantos-hue/Group_M.git
cd Group_M
```

### 2. Create and activate a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install and start Ollama

Download and install Ollama from [https://ollama.com/download](https://ollama.com/download), then start the server:

```bash
ollama serve
```

The application will automatically pull the required models (`llava:7b` and `llama3.2:3b`) on first run if they are not already available locally. You may also pull them manually in advance:

```bash
ollama pull llava:7b
ollama pull llama3.2:3b
```

---

## How to Run the Project

### Download datasets only (CLI)

To download the OWID environmental datasets without launching the UI:

```bash
python main.py
```

This will fetch all five CSV datasets from Our World in Data and save them to the `downloads/` directory.

### Launch the Streamlit application

```bash
streamlit run app/streamlit_app.py
```

The application will open in your default browser at `http://localhost:8501`. Use the sidebar to switch between the **Maps** and **Satellite Analysis** pages.

---

## Usage

### Maps page

1. Open the application and select **Maps** from the sidebar.
2. Use the dropdown to select an environmental indicator (e.g. `red_list_index`, `annual_deforestation`).
3. A world choropleth map will render with country values for the most recent year in the dataset.
4. Scroll down to view the Top 5 and Bottom 5 countries for the selected indicator, along with a comparison bar chart.

### Satellite Analysis page

1. Select **Satellite Analysis** from the sidebar.
2. Enter a **latitude** and **longitude** for the area you want to investigate (e.g. `-3.4653`, `-62.2159` for the Amazon basin).
3. Adjust the **zoom level** (1 = global, 20 = street level; values between 10 and 15 work well for landscape analysis).
4. Click **Analyze Area**.
5. The application will:
   - Download the satellite image from ESRI World Imagery.
   - Display the image in the interface.
   - Generate a detailed textual description using the LLaVA vision model.
   - Assess environmental risk using the Llama 3.2 model.
   - Display the risk report with a danger flag, confidence level, summary, and reasons.
   - Cache the result in `database/images.csv` for instant retrieval on repeat queries.

> If the same coordinates and zoom level have been analysed before, the stored result is retrieved immediately without re-running the AI pipeline.

---

## Environmental Danger Detection Examples

The following examples are drawn from real analyses stored in the project's `database/images.csv`.

### Example 1 — Active Mining Site (Uzbekistan)

**Coordinates:** 41.498°N, 64.572°E | **Zoom:** 13

The satellite image of this region in central Uzbekistan revealed multiple large open pits consistent with active mining operations, alongside extensive areas of bare soil, visible scarring of the landscape, fire-affected vegetation, and signs of accelerating erosion. Urban expansion was also detected, suggesting that industrial development is encroaching on previously natural land.

The AI pipeline flagged the area as **Danger: Yes** with **High** confidence. The risk assessment identified deforestation, land degradation from mining, and urban encroachment as the primary threats. This type of detection is particularly valuable in remote, sparsely monitored regions where ground-based inspection is logistically difficult — satellite-based AI screening can alert environmental agencies to degradation events far earlier than traditional monitoring.

### Example 2 — Amazon Rainforest Degradation (Brazil)

**Coordinates:** -3.4653°S, -62.2159°W | **Zoom:** 10

The image captured a large area of the Amazon basin in Brazil, showing dense green forest canopy interspersed with patches of deforested land, fire scars, roads cutting through previously intact forest, and evidence of human settlements expanding into natural habitat. Water bodies were visible, and the overall pattern strongly indicated progressive human-driven fragmentation of the ecosystem.

The model assessed the area as **Danger: Yes** with **High** confidence, citing deforestation from agriculture or mining, wildfire damage, and urban encroachment as the key concerns. The Amazon is one of the most biodiverse regions on Earth and a critical carbon sink; early automated detection of degradation in areas like this directly supports conservation efforts and international climate commitments.

### Example 3 — Intact Urban Area, No Environmental Risk (Copenhagen, Denmark)

**Coordinates:** 55.684°N, 12.593°E | **Zoom:** 20

At maximum zoom, the application captured a ground-level aerial view of a structured urban courtyard in a Copenhagen's Royal Palace showing paved surfaces, walkways, and built infrastructure. No vegetation, water bodies, or signs of land degradation were detected.

The model returned **Danger: No** with **Low** confidence, concluding that the area shows no signs of environmental threat. This example demonstrates the system's ability to correctly distinguish between genuinely at-risk natural environments and well-maintained urban areas, reducing false positives and ensuring that alerts are meaningful. The low confidence reflects the limited environmental information available in a purely urban image — an appropriate and calibrated response from the model.

---

## Contribution to the UN Sustainable Development Goals (SDGs)

Environmental degradation is one of the defining challenges of our time. Forests are being cleared at alarming rates, biodiversity is collapsing, and the land that billions of people and countless species depend upon is being lost faster than it can recover. Project Okavango was built with the conviction that better information leads to better outcomes — and that accessible, automated environmental monitoring tools can meaningfully contribute to the global effort to reverse these trends.

The project most directly supports **SDG 15 — Life on Land**, which calls for the protection, restoration, and sustainable use of terrestrial ecosystems. By combining global indicators of forest loss, land degradation, and biodiversity decline (through the Red List Index) with AI-powered satellite image analysis, the application provides exactly the kind of evidence-based monitoring that SDG 15 requires. When an area in the Amazon or central Asia is flagged as showing signs of mining damage or deforestation, that information can — in the right hands — trigger conservation action before irreversible harm is done.

The project also has a strong connection to **SDG 13 — Climate Action**. Forests are major carbon sinks, and their destruction accelerates climate change. Monitoring deforestation and land degradation at scale is therefore not just a biodiversity concern but a climate one. The application's annual forest area change datasets directly track one of the most important variables in climate modelling, and the satellite analysis tool allows users to ground-truth those statistics with real imagery.

**SDG 11 — Sustainable Cities and Communities** is relevant in the context of the urban encroachment detection capability. One of the clearest signals the satellite analysis model looks for is the expansion of human settlements into previously natural land — a pattern that is both a driver of habitat destruction and an indicator of unsustainable urban growth. Identifying these frontiers early gives planners and policymakers the opportunity to intervene.

Finally, the project aligns with **SDG 3 — Good Health and Well-Being** to the extent that environmental degradation — polluted water sources, degraded land, loss of natural buffers against flooding and disease — directly affects human health, particularly in lower-income communities with fewer resources to adapt.

What makes this project meaningful, beyond the technical implementation, is that it democratises access to environmental intelligence. High-quality satellite analysis has historically been the domain of well-funded research institutions and government agencies. By building a tool that runs entirely on local open-source AI models and free satellite imagery, we wanted to explore what it might look like to put that capability in the hands of a wider audience — researchers, activists, educators, and curious citizens who care about the planet and want to understand what is happening to it.

---

## Running Tests

The project includes a test suite covering data download and merge logic.

```bash
pytest tests/
```

Tests use `pytest`'s `monkeypatch` and `tmp_path` fixtures to avoid real HTTP requests and filesystem side effects. The test suite covers:

- `test_download.py` — verifies that all configured datasets are downloaded and written correctly to disk, with mocked HTTP responses.
- `test_merge.py` — verifies that the world map merge correctly uses only the most recent year's data and renames the value column to the standardised `value` field.

---

## Project Structure

Group_M/
├── app/
│   └── streamlit_app.py       # Main Streamlit UI application
├── database/
│   └── images.csv             # Persistent analysis results database
├── downloads/                 # Downloaded CSV datasets and map files
│   ├── annual_change_forest_area.csv
│   ├── annual_deforestation.csv
│   ├── ne_110m_admin_0_countries.zip
│   ├── red_list_index.csv
│   ├── share_degraded_land.csv
│   └── share_protected_land.csv
├── images/                    # Downloaded satellite images
├── notebooks/                 # Jupyter notebooks (exploratory work)
├── okavango/
│   ├── __init__.py
│   └── data_manager.py        # Data download, loading, and merge logic
├── tests/
│   ├── conftest.py            # Pytest path configuration
│   ├── test_download.py       # Tests for CSV download logic
│   └── test_merge.py          # Tests for world map merge logic
├── .gitignore
├── LICENSE
├── main.py                    # CLI entry point for dataset download
├── models.yaml                # AI model names and prompts configuration
├── requirements.txt           # Python dependencies
└── README.md


