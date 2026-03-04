from pathlib import Path
import requests
import pandas as pd
import geopandas as gpd
from pydantic import BaseModel
from pathlib import Path

DOWNLOADS_DIR = Path("downloads")


DATASETS = {
    "annual_change_forest_area": "https://ourworldindata.org/grapher/annual-change-forest-area.csv",
    "annual_deforestation": "https://ourworldindata.org/grapher/annual-deforestation.csv",
    "share_protected_land": "https://ourworldindata.org/grapher/terrestrial-protected-areas.csv",
    "share_degraded_land": "https://ourworldindata.org/grapher/share-degraded-land.csv",
    "red_list_index": "https://ourworldindata.org/grapher/red-list-index.csv",
}


def download_csv(url: str, filename: str) -> Path:
    DOWNLOADS_DIR.mkdir(exist_ok=True)

    response = requests.get(url)
    response.raise_for_status()

    file_path = DOWNLOADS_DIR / filename
    file_path.write_bytes(response.content)
    return file_path


def download_all_datasets() -> dict[str, Path]:
    paths = {}

    for name, url in DATASETS.items():
        filename = f"{name}.csv"
        path = download_csv(url=url, filename=filename)
        paths[name] = path

    return paths


def load_datasets(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    dataframes: dict[str, pd.DataFrame] = {}

    for name, path in paths.items():
        df = pd.read_csv(path)
        dataframes[name] = df

    return dataframes


NATURAL_EARTH_ZIP = DOWNLOADS_DIR / "ne_110m_admin_0_countries.zip"


def load_world_map(downloads_dir: Path, natural_earth_zip: str) -> gpd.GeoDataFrame:
    path = downloads_dir / natural_earth_zip
    if not path.exists():
        raise FileNotFoundError(f"Falta o ficheiro: {path}")
    return gpd.read_file(path)


def latest_year_snapshot(df: pd.DataFrame) -> pd.DataFrame:
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
    snapshot = latest_year_snapshot(df)

    merged = world.merge(
        snapshot[["Code", "Entity", "Year", value_column]],
        left_on="SOV_A3",
        right_on="Code",
        how="left",
    ).rename(columns={value_column: "value"})  # <- ISTO

    return gpd.GeoDataFrame(merged, geometry="geometry", crs=world.crs)


def load_all_csvs(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    return {name: pd.read_csv(path) for name, path in paths.items()}


def detect_value_column(df: pd.DataFrame) -> str:
    base_cols = {"Entity", "Code", "Year"}
    candidates = [c for c in df.columns if c not in base_cols]

    if len(candidates) != 1:
        raise ValueError(f"Não consegui identificar a coluna de valores. Colunas extra: {candidates}")

    return candidates[0]


def build_merged_maps() -> dict[str, gpd.GeoDataFrame]:
    paths = download_all_datasets()
    dfs = load_all_csvs(paths)
    world = load_world_map()

    merged_maps: dict[str, gpd.GeoDataFrame] = {}

    for name, df in dfs.items():
        value_col = detect_value_column(df)
        merged_maps[name] = merge_world_with_dataset(world, df, value_col)

    return merged_maps


class OkavangoConfig(BaseModel):
    downloads_dir: Path = Path("downloads")
    natural_earth_zip: str = "ne_110m_admin_0_countries.zip"


class OkavangoData:
    def __init__(self, config: OkavangoConfig):
        self.config = config

        # Function 1
        self.paths = download_all_datasets()

        # read csvs -> atributos
        self.dfs = load_all_csvs(self.paths)

        # map
        self.world = load_world_map(
            downloads_dir=self.config.downloads_dir,
            natural_earth_zip=self.config.natural_earth_zip,
        )

        # Function 2 (merge)
        self.merged_maps = {}
        for name, df in self.dfs.items():
            value_col = detect_value_column(df)
            self.merged_maps[name] = merge_world_with_dataset(
                world=self.world,
                df=df,
                value_column=value_col,
            )


