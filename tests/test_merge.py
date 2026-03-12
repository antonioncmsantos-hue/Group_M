from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from okavango.data_manager import merge_world_with_dataset


def test_merge_world_with_dataset_uses_latest_year():
    """
    Verify that the merge uses only the most recent year available in the dataset.

    This test builds a small synthetic world GeoDataFrame and a tabular dataset
    containing two years of observations for each country. It then checks that
    the merged result keeps the values from the latest year and exposes them
    through the standardised ``value`` column.

    Returns
    -------
    None
        This test performs assertions and does not return a value.

    Notes
    -----
    The expected behaviour is:
    - the original indicator column is renamed to ``value``,
    - the ``Year`` column is preserved,
    - the values for Portugal and Spain come from year 2024.
    """
    # Minimal world map sample with two countries and simple point geometries.
    world = gpd.GeoDataFrame(
        {
            "SOV_A3": ["PRT", "ESP"],
            "ADMIN": ["Portugal", "Spain"],
            "geometry": [Point(0, 0), Point(1, 1)],
        },
        geometry="geometry",
        crs="EPSG:4326",
    )

    # Example OWID-style dataset containing two years per country.
    df = pd.DataFrame(
        {
            "Entity": ["Portugal", "Portugal", "Spain", "Spain"],
            "Code": ["PRT", "PRT", "ESP", "ESP"],
            "Year": [2023, 2024, 2023, 2024],
            "MyValue": [10, 11, 20, 21],
        }
    )

    # Merge the map with the latest-year snapshot of the tabular dataset.
    merged = merge_world_with_dataset(world=world, df=df, value_column="MyValue")

    # The merged dataset should expose the indicator through the standardised name.
    assert "value" in merged.columns
    assert "Year" in merged.columns

    prt_val = merged.loc[merged["SOV_A3"] == "PRT", "value"].iloc[0]
    esp_val = merged.loc[merged["SOV_A3"] == "ESP", "value"].iloc[0]
    year_prt = merged.loc[merged["SOV_A3"] == "PRT", "Year"].iloc[0]
    year_esp = merged.loc[merged["SOV_A3"] == "ESP", "Year"].iloc[0]

    # Confirm that the values come from the most recent year, 2024.
    assert prt_val == 11
    assert esp_val == 21
    assert int(year_prt) == 2024
    assert int(year_esp) == 2024