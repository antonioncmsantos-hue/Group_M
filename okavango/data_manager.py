# Imports for path handling, HTTP requests, data manipulation, geospatial data, and config validation.
from pathlib import Path
import requests
import pandas as pd
import geopandas as gpd
from pydantic import BaseModel

# Default directory where all downloaded CSV files will be stored.
DOWNLOADS_DIR = Path("downloads")

# Mapping of dataset names to their respective Our World in Data CSV URLs.
DATASETS = {
    "annual_change_forest_area": "https://ourworldindata.org/grapher/annual-change-forest-area.csv",
    "annual_deforestation": "https://ourworldindata.org/grapher/annual-deforestation.csv",
    "share_protected_land": "https://ourworldindata.org/grapher/terrestrial-protected-areas.csv",
    "share_degraded_land": "https://ourworldindata.org/grapher/share-degraded-land.csv",
    "red_list_index": "https://ourworldindata.org/grapher/red-list-index.csv",
}


def download_csv(url: str, filename: str, downloads_dir: Path) -> Path:
    """
    Download a single CSV file from a URL and save it to the downloads directory.

    Parameters
    ----------
    url : str
        The remote URL pointing to the CSV file to download.
    filename : str
        The name of the file to save locally inside DOWNLOADS_DIR.

    Returns
    -------
    Path
        The path to the saved file on disk.

    Raises
    ------
    requests.HTTPError
        If the HTTP request returns an unsuccessful status code.

    Examples
    --------
    >>> path = download_csv("https://example.com/data.csv", "data.csv")
    >>> path.exists()
    True
    """

    downloads_dir.mkdir(parents=True, exist_ok=True)

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    file_path = downloads_dir / filename
    file_path.write_bytes(response.content)
    return file_path


def download_all_datasets(downloads_dir: Path) -> dict[str, Path]:
    """
    Download all datasets defined in DATASETS to downloads_dir.
    """
    paths: dict[str, Path] = {}

    for name, url in DATASETS.items():
        filename = f"{name}.csv"
        path = download_csv(url=url, filename=filename, downloads_dir=downloads_dir)
        paths[name] = path

    return paths


def load_datasets(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    """
    Load a collection of CSV files from disk into pandas DataFrames.

    Parameters
    ----------
    paths : dict[str, Path]
        A dictionary mapping dataset names to their local file paths.

    Returns
    -------
    dict[str, pd.DataFrame]
        A dictionary mapping each dataset name to its loaded DataFrame.

    Examples
    --------
    >>> dfs = load_datasets({"red_list_index": Path("downloads/red_list_index.csv")})
    >>> isinstance(dfs["red_list_index"], pd.DataFrame)
    True
    """
    dataframes: dict[str, pd.DataFrame] = {}

    for name, path in paths.items():
        df = pd.read_csv(path)
        dataframes[name] = df

    return dataframes


def load_world_map(downloads_dir: Path, natural_earth_zip: str) -> gpd.GeoDataFrame:
    """
    Load the Natural Earth world map from a local zip file.
    """
    path = downloads_dir / natural_earth_zip

    if not path.exists():
        raise FileNotFoundError(f"Natural Earth zip not found: {path}")

    return gpd.read_file(path)


NATURAL_EARTH_URL = (
    "https://naciscdn.org/naturalearth/110m/cultural/"
    "ne_110m_admin_0_countries.zip"
)
NATURAL_EARTH_FILENAME = "ne_110m_admin_0_countries.zip"


def download_natural_earth_map(
    downloads_dir: Path,
    url: str = NATURAL_EARTH_URL,
    filename: str = NATURAL_EARTH_FILENAME,
) -> Path:
    """
    Download the Natural Earth countries zip file into downloads_dir.
    """
    downloads_dir.mkdir(parents=True, exist_ok=True)
    path = downloads_dir / filename

    if not path.exists():
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        path.write_bytes(response.content)

    return path




def latest_year_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter a DataFrame to keep only rows from the most recent year available.

    Parameters
    ----------
    df : pd.DataFrame
        A DataFrame with at least the columns 'Code' and 'Year'.

    Returns
    -------
    pd.DataFrame
        A copy of the input DataFrame containing only rows from the latest year,
        with rows missing 'Code' or a valid numeric 'Year' removed.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"Entity": ["Portugal", "Portugal"], "Code": ["PRT", "PRT"], "Year": [2023, 2024], "Value": [10, 11]})
    >>> latest_year_snapshot(df)["Year"].unique()
    array([2024])
    """
    df = df.dropna(subset=["Code"]).copy()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df.dropna(subset=["Year"])

    latest_year = int(df["Year"].max())
    return df[df["Year"] == latest_year].copy()


def merge_world_with_dataset(
    world: gpd.GeoDataFrame,
    df: pd.DataFrame,
    value_column: str,
) -> gpd.GeoDataFrame:
    """
    Merge a world map GeoDataFrame with an OWID dataset using the latest year snapshot.

    Parameters
    ----------
    world : gpd.GeoDataFrame
        The world map GeoDataFrame containing a 'SOV_A3' country code column.
    df : pd.DataFrame
        An Our World in Data DataFrame with 'Entity', 'Code', 'Year', and a value column.
    value_column : str
        The name of the column in df that holds the indicator values.

    Returns
    -------
    gpd.GeoDataFrame
        A GeoDataFrame with world map geometries joined to the dataset values.
        The value column is renamed to 'value' for consistency.

    Notes
    -----
    The merge is a left join on 'SOV_A3' (world) and 'Code' (dataset), so countries
    without data will appear in the result with NaN in the value column.

    Examples
    --------
    >>> merged = merge_world_with_dataset(world, df, "RedListIndex")
    >>> "value" in merged.columns
    True
    """
    snapshot = latest_year_snapshot(df)

    merged = world.merge(
        snapshot[["Code", "Entity", "Year", value_column]],
        left_on="SOV_A3",
        right_on="Code",
        how="left",
    ).rename(columns={value_column: "value"})

    return gpd.GeoDataFrame(merged, geometry="geometry", crs=world.crs)


def load_all_csvs(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    """
    Load all CSV files from a dictionary of paths into pandas DataFrames.

    Parameters
    ----------
    paths : dict[str, Path]
        A dictionary mapping dataset names to their local CSV file paths.

    Returns
    -------
    dict[str, pd.DataFrame]
        A dictionary mapping each dataset name to its loaded DataFrame.

    Examples
    --------
    >>> dfs = load_all_csvs({"red_list_index": Path("downloads/red_list_index.csv")})
    >>> isinstance(dfs["red_list_index"], pd.DataFrame)
    True
    """
    return {name: pd.read_csv(path) for name, path in paths.items()}


def detect_value_column(df: pd.DataFrame) -> str:
    """
    Automatically detect the single indicator value column in an OWID DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        A DataFrame expected to have 'Entity', 'Code', 'Year', and exactly one
        additional column holding the indicator values.

    Returns
    -------
    str
        The name of the detected value column.

    Raises
    ------
    ValueError
        If there is not exactly one non-standard column in the DataFrame.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"Entity": [], "Code": [], "Year": [], "RedListIndex": []})
    >>> detect_value_column(df)
    'RedListIndex'
    """
    base_cols = {"Entity", "Code", "Year"}
    candidates = [c for c in df.columns if c not in base_cols]

    if len(candidates) != 1:
        raise ValueError(f"Não consegui identificar a coluna de valores. Colunas extra: {candidates}")

    return candidates[0]


def build_merged_maps(
    downloads_dir: Path,
    natural_earth_zip: str,
) -> dict[str, gpd.GeoDataFrame]:
    paths = download_all_datasets(downloads_dir)
    dfs = load_all_csvs(paths)
    world = load_world_map(downloads_dir, natural_earth_zip)

    merged_maps: dict[str, gpd.GeoDataFrame] = {}

    for name, df in dfs.items():
        value_col = detect_value_column(df)
        merged_maps[name] = merge_world_with_dataset(world, df, value_col)

    return merged_maps

class OkavangoConfig(BaseModel):
    """
    Configuration model for the OkavangoData class.

    Parameters
    ----------
    downloads_dir : Path
        Directory where datasets and map files are stored. Defaults to 'downloads'.
    natural_earth_zip : str
        Filename of the Natural Earth zip file for the world map.
        Defaults to 'ne_110m_admin_0_countries.zip'.
    """
    
    downloads_dir: Path = Path("downloads")
    natural_earth_url: str = (
        "https://naciscdn.org/naturalearth/110m/cultural/"
        "ne_110m_admin_0_countries.zip"
    )
    natural_earth_zip: str = "ne_110m_admin_0_countries.zip"


class OkavangoConfig(BaseModel):
    downloads_dir: Path = Path("downloads")
    natural_earth_url: str = (
        "https://naciscdn.org/naturalearth/110m/cultural/"
        "ne_110m_admin_0_countries.zip"
    )
    natural_earth_zip: str = "ne_110m_admin_0_countries.zip"

    """
    Main data class that downloads, loads, and merges all environmental datasets.

    Parameters
    ----------
    config : OkavangoConfig
        Configuration object specifying download directory and map file paths.

    Attributes
    ----------
    config : OkavangoConfig
        The configuration used to initialise this instance.
    paths : dict[str, Path]
        File paths of all downloaded CSV datasets.
    dfs : dict[str, pd.DataFrame]
        Raw DataFrames loaded from each downloaded CSV.
    world : gpd.GeoDataFrame
        The Natural Earth world map GeoDataFrame.
    merged_maps : dict[str, gpd.GeoDataFrame]
        One merged GeoDataFrame per dataset, ready for visualisation.

    Examples
    --------
    >>> data = OkavangoData(OkavangoConfig())
    >>> "red_list_index" in data.merged_maps
    True
    """
    
class OkavangoData:
    def __init__(self, config: OkavangoConfig | None = None) -> None:
        self.config = config or OkavangoConfig()

        # Download all tabular datasets and store their local paths.
        self.paths = download_all_datasets(self.config.downloads_dir)

        # Download the Natural Earth map zip file.
        download_natural_earth_map(
            downloads_dir=self.config.downloads_dir,
            url=self.config.natural_earth_url,
            filename=self.config.natural_earth_zip,
        )

        # Read all CSVs into DataFrames.
        self.dfs = load_all_csvs(self.paths)

        # Load the world map GeoDataFrame from the local Natural Earth zip file.
        self.world = load_world_map(
            downloads_dir=self.config.downloads_dir,
            natural_earth_zip=self.config.natural_earth_zip,
        )

        # Merge each dataset with the world map.
        self.merged_maps = {}
        for name, df in self.dfs.items():
            value_col = detect_value_column(df)
            self.merged_maps[name] = merge_world_with_dataset(
                world=self.world,
                df=df,
                value_column=value_col,
            )