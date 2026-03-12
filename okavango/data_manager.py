from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from pydantic import BaseModel

# Default folder used to store downloaded tabular datasets and map files.
DOWNLOADS_DIR = Path("downloads")

# Mapping between internal dataset names and their OWID CSV endpoints.
DATASETS = {
    "annual_change_forest_area": "https://ourworldindata.org/grapher/annual-change-forest-area.csv",
    "annual_deforestation": "https://ourworldindata.org/grapher/annual-deforestation.csv",
    "share_protected_land": "https://ourworldindata.org/grapher/terrestrial-protected-areas.csv",
    "share_degraded_land": "https://ourworldindata.org/grapher/share-degraded-land.csv",
    "red_list_index": "https://ourworldindata.org/grapher/red-list-index.csv",
}

# Natural Earth source used to retrieve the world country boundaries shapefile.
NATURAL_EARTH_URL = (
    "https://naciscdn.org/naturalearth/110m/cultural/"
    "ne_110m_admin_0_countries.zip"
)
NATURAL_EARTH_FILENAME = "ne_110m_admin_0_countries.zip"


def download_csv(url: str, filename: str, downloads_dir: Path = DOWNLOADS_DIR) -> Path:
    """
    Download a single CSV file and save it locally.

    This function retrieves a CSV file from a remote URL, creates the target
    directory if necessary, and writes the response content to disk.

    Parameters
    ----------
    url : str
        URL of the CSV file to download.
    filename : str
        Local filename to use when saving the file.
    downloads_dir : Path, optional
        Directory where the file will be stored, by default ``DOWNLOADS_DIR``.

    Returns
    -------
    Path
        Full path to the saved CSV file.

    Raises
    ------
    requests.HTTPError
        Raised if the HTTP request fails or returns an unsuccessful status code.

    Examples
    --------
    >>> path = download_csv("https://example.com/data.csv", "data.csv")
    >>> path.name
    'data.csv'
    """
    downloads_dir.mkdir(parents=True, exist_ok=True)

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    file_path = downloads_dir / filename
    file_path.write_bytes(response.content)
    return file_path


def download_all_datasets(downloads_dir: Path = DOWNLOADS_DIR) -> dict[str, Path]:
    """
    Download all OWID datasets defined in ``DATASETS``.

    Parameters
    ----------
    downloads_dir : Path, optional
        Directory where all CSV files will be saved, by default ``DOWNLOADS_DIR``.

    Returns
    -------
    dict[str, Path]
        Dictionary mapping each dataset name to the corresponding downloaded file path.

    Notes
    -----
    The output keys match the keys defined in the global ``DATASETS`` dictionary.
    """
    paths: dict[str, Path] = {}

    # Download each configured dataset and keep track of its local file path.
    for name, url in DATASETS.items():
        filename = f"{name}.csv"
        paths[name] = download_csv(url=url, filename=filename, downloads_dir=downloads_dir)

    return paths


def load_all_csvs(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    """
    Load multiple CSV files into pandas DataFrames.

    Parameters
    ----------
    paths : dict[str, Path]
        Dictionary mapping dataset names to local file paths.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary mapping dataset names to loaded DataFrames.

    Examples
    --------
    >>> dfs = load_all_csvs({"example": Path("downloads/example.csv")})
    >>> isinstance(dfs, dict)
    True
    """
    return {name: pd.read_csv(path) for name, path in paths.items()}


def load_datasets(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    """
    Load multiple CSV files into pandas DataFrames.

    This function is kept as a compatibility alias for ``load_all_csvs``.

    Parameters
    ----------
    paths : dict[str, Path]
        Dictionary mapping dataset names to local file paths.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary mapping dataset names to loaded DataFrames.
    """
    return load_all_csvs(paths)


def download_natural_earth_map(
    downloads_dir: Path = DOWNLOADS_DIR,
    url: str = NATURAL_EARTH_URL,
    filename: str = NATURAL_EARTH_FILENAME,
) -> Path:
    """
    Download the Natural Earth world map archive if it is not already stored locally.

    Parameters
    ----------
    downloads_dir : Path, optional
        Directory where the zip file will be saved, by default ``DOWNLOADS_DIR``.
    url : str, optional
        Source URL of the Natural Earth zip file, by default ``NATURAL_EARTH_URL``.
    filename : str, optional
        Local filename for the zip file, by default ``NATURAL_EARTH_FILENAME``.

    Returns
    -------
    Path
        Path to the downloaded or already existing Natural Earth archive.

    Raises
    ------
    requests.HTTPError
        Raised if the map download request fails.
    """
    downloads_dir.mkdir(parents=True, exist_ok=True)
    path = downloads_dir / filename

    # Avoid downloading the archive again if it already exists locally.
    if not path.exists():
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        path.write_bytes(response.content)

    return path


def load_world_map(
    downloads_dir: Path = DOWNLOADS_DIR,
    natural_earth_zip: str = NATURAL_EARTH_FILENAME,
) -> gpd.GeoDataFrame:
    """
    Load the Natural Earth world map from a local zip archive.

    Parameters
    ----------
    downloads_dir : Path, optional
        Directory where the zip file is stored, by default ``DOWNLOADS_DIR``.
    natural_earth_zip : str, optional
        Name of the Natural Earth zip file, by default ``NATURAL_EARTH_FILENAME``.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame containing world country geometries and metadata.

    Raises
    ------
    FileNotFoundError
        Raised if the specified Natural Earth zip file does not exist locally.
    """
    path = downloads_dir / natural_earth_zip

    if not path.exists():
        raise FileNotFoundError(f"Natural Earth zip not found: {path}")

    return gpd.read_file(path)


def latest_year_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only the rows corresponding to the most recent year in a dataset.

    The function removes rows without a valid country code, coerces the ``Year``
    column to numeric values, discards invalid years, and then filters the
    DataFrame to the latest year available.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame with at least ``Code`` and ``Year`` columns.

    Returns
    -------
    pandas.DataFrame
        Filtered copy of the input DataFrame containing only rows from the
        latest available year.

    Examples
    --------
    >>> df = pd.DataFrame({
    ...     "Entity": ["Portugal", "Portugal"],
    ...     "Code": ["PRT", "PRT"],
    ...     "Year": [2023, 2024],
    ...     "Value": [10, 11],
    ... })
    >>> latest_year_snapshot(df)["Year"].iloc[0]
    2024
    """
    # Remove entries without a valid country code before filtering by year.
    cleaned_df = df.dropna(subset=["Code"]).copy()
    cleaned_df["Year"] = pd.to_numeric(cleaned_df["Year"], errors="coerce")
    cleaned_df = cleaned_df.dropna(subset=["Year"])

    latest_year = int(cleaned_df["Year"].max())
    return cleaned_df[cleaned_df["Year"] == latest_year].copy()


def detect_value_column(df: pd.DataFrame) -> str:
    """
    Detect the indicator column in an OWID-style dataset.

    The expected schema is one identifier block made of ``Entity``, ``Code``,
    and ``Year``, plus exactly one additional column containing the indicator
    values.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame expected to contain ``Entity``, ``Code``, ``Year``, and one
        value column.

    Returns
    -------
    str
        Name of the detected indicator value column.

    Raises
    ------
    ValueError
        Raised if the DataFrame does not contain exactly one non-standard column.

    Examples
    --------
    >>> df = pd.DataFrame({
    ...     "Entity": [],
    ...     "Code": [],
    ...     "Year": [],
    ...     "RedListIndex": [],
    ... })
    >>> detect_value_column(df)
    'RedListIndex'
    """
    base_columns = {"Entity", "Code", "Year"}
    candidate_columns = [col for col in df.columns if col not in base_columns]

    if len(candidate_columns) != 1:
        raise ValueError(
            f"Could not identify the value column. Extra columns found: {candidate_columns}"
        )

    return candidate_columns[0]


def merge_world_with_dataset(
    world: gpd.GeoDataFrame,
    df: pd.DataFrame,
    value_column: str,
) -> gpd.GeoDataFrame:
    """
    Merge a world map with the most recent snapshot of an environmental dataset.

    The merge is performed as a left join between the Natural Earth country
    codes in ``world['SOV_A3']`` and the OWID country codes in ``df['Code']``.
    The selected indicator column is renamed to ``value`` to provide a
    consistent name for downstream visualisation.

    Parameters
    ----------
    world : geopandas.GeoDataFrame
        World map GeoDataFrame containing a ``SOV_A3`` country code column.
    df : pandas.DataFrame
        Dataset DataFrame containing ``Entity``, ``Code``, ``Year``, and the
        selected value column.
    value_column : str
        Name of the indicator column to merge.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame resulting from the merge, with the indicator column renamed
        to ``value``.

    Notes
    -----
    Countries that do not have matching data in the dataset are preserved in the
    output and will contain missing values in the merged columns.
    """
    # Reduce the input dataset to the most recent year before merging.
    snapshot = latest_year_snapshot(df)

    merged = world.merge(
        snapshot[["Code", "Entity", "Year", value_column]],
        left_on="SOV_A3",
        right_on="Code",
        how="left",
    ).rename(columns={value_column: "value"})

    return gpd.GeoDataFrame(merged, geometry="geometry", crs=world.crs)


def build_merged_maps(
    downloads_dir: Path = DOWNLOADS_DIR,
    natural_earth_zip: str = NATURAL_EARTH_FILENAME,
) -> dict[str, gpd.GeoDataFrame]:
    """
    Build merged geospatial datasets for all configured OWID indicators.

    This function downloads the Natural Earth map and all configured OWID CSVs,
    loads them into memory, detects the value column for each dataset, and
    returns one merged GeoDataFrame per indicator.

    Parameters
    ----------
    downloads_dir : Path, optional
        Directory where datasets and map files are stored, by default
        ``DOWNLOADS_DIR``.
    natural_earth_zip : str, optional
        Name of the Natural Earth zip file, by default
        ``NATURAL_EARTH_FILENAME``.

    Returns
    -------
    dict[str, geopandas.GeoDataFrame]
        Dictionary mapping dataset names to merged GeoDataFrames.

    Examples
    --------
    >>> merged_maps = build_merged_maps()
    >>> isinstance(merged_maps, dict)
    True
    """
    # Ensure the base world map file exists locally.
    download_natural_earth_map(downloads_dir=downloads_dir, filename=natural_earth_zip)

    # Download and load all configured tabular datasets.
    paths = download_all_datasets(downloads_dir=downloads_dir)
    dfs = load_all_csvs(paths)

    # Load the geospatial world map used as the merge base.
    world = load_world_map(downloads_dir=downloads_dir, natural_earth_zip=natural_earth_zip)

    merged_maps: dict[str, gpd.GeoDataFrame] = {}

    # For each dataset, detect its indicator column and merge it with the map.
    for name, df in dfs.items():
        value_column = detect_value_column(df)
        merged_maps[name] = merge_world_with_dataset(
            world=world,
            df=df,
            value_column=value_column,
        )

    return merged_maps


class OkavangoConfig(BaseModel):
    """
    Configuration model for ``OkavangoData``.

    Parameters
    ----------
    downloads_dir : Path
        Directory where datasets and map files are stored.
    natural_earth_url : str
        Source URL of the Natural Earth archive.
    natural_earth_zip : str
        Filename used to store the Natural Earth archive locally.
    """

    downloads_dir: Path = DOWNLOADS_DIR
    natural_earth_url: str = NATURAL_EARTH_URL
    natural_earth_zip: str = NATURAL_EARTH_FILENAME


class OkavangoData:
    """
    Main data manager class for the Okavango project.

    This class centralises the full data preparation workflow:
    downloading datasets, downloading the Natural Earth world map,
    loading all files into memory, and building one merged GeoDataFrame
    per environmental indicator.

    Parameters
    ----------
    config : OkavangoConfig | None, optional
        Configuration object controlling download paths and map settings.
        If ``None``, a default ``OkavangoConfig`` is created.

    Attributes
    ----------
    config : OkavangoConfig
        Configuration used by the instance.
    paths : dict[str, Path]
        Dictionary of downloaded dataset file paths.
    dfs : dict[str, pandas.DataFrame]
        Dictionary of raw tabular datasets loaded into memory.
    world : geopandas.GeoDataFrame
        Natural Earth world map GeoDataFrame.
    merged_maps : dict[str, geopandas.GeoDataFrame]
        Dictionary of merged GeoDataFrames ready for visualisation.

    Examples
    --------
    >>> data = OkavangoData()
    >>> "red_list_index" in data.merged_maps
    True
    """

    def __init__(self, config: OkavangoConfig | None = None) -> None:
        """
        Initialise the data manager and prepare all merged datasets.

        Parameters
        ----------
        config : OkavangoConfig | None, optional
            Configuration object controlling paths and map download settings.
            If ``None``, a default configuration is used.

        Notes
        -----
        During initialisation, the class:
        1. Downloads all configured CSV datasets.
        2. Downloads the Natural Earth map archive if needed.
        3. Loads all datasets into memory.
        4. Loads the world map.
        5. Builds one merged GeoDataFrame per dataset.
        """
        self.config = config or OkavangoConfig()

        # Download all configured environmental datasets.
        self.paths = download_all_datasets(self.config.downloads_dir)

        # Ensure the Natural Earth map archive exists locally.
        download_natural_earth_map(
            downloads_dir=self.config.downloads_dir,
            url=self.config.natural_earth_url,
            filename=self.config.natural_earth_zip,
        )

        # Load all CSV datasets into pandas DataFrames.
        self.dfs = load_all_csvs(self.paths)

        # Load the world map used as the geospatial merge base.
        self.world = load_world_map(
            downloads_dir=self.config.downloads_dir,
            natural_earth_zip=self.config.natural_earth_zip,
        )

        self.merged_maps: dict[str, gpd.GeoDataFrame] = {}

        # Build one merged GeoDataFrame per configured dataset.
        for name, df in self.dfs.items():
            value_column = detect_value_column(df)
            self.merged_maps[name] = merge_world_with_dataset(
                world=self.world,
                df=df,
                value_column=value_column,
            )