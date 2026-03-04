# Imports for data manipulation, geospatial, geometry, and the function under test.
from __future__ import annotations

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from okavango.data_manager import merge_world_with_dataset


def test_merge_world_with_dataset_uses_latest_year():
    # Fake GeoDataFrame with two countries (PRT, ESP), mimicking a Natural Earth dataset.
    world = gpd.GeoDataFrame(
        {
            "SOV_A3": ["PRT", "ESP"],
            "ADMIN": ["Portugal", "Spain"],
            "geometry": [Point(0, 0), Point(1, 1)],
        },
        geometry="geometry",
        crs="EPSG:4326",
    )

    # Fake OWID DataFrame with 2 years per country (latest = 2024).
    df = pd.DataFrame(
        {
            "Entity": ["Portugal", "Portugal", "Spain", "Spain"],
            "Code": ["PRT", "PRT", "ESP", "ESP"],
            "Year": [2023, 2024, 2023, 2024],
            "MyValue": [10, 11, 20, 21],
        }
    )
    # Run the merge function with the fake data.
    merged = merge_world_with_dataset(world=world, df=df, value_column="MyValue")

    # Check that the expected columns exist in the result.
    assert "MyValue" in merged.columns
    assert "Year" in merged.columns

    prt_val = merged.loc[merged["SOV_A3"] == "PRT", "MyValue"].iloc[0]
    esp_val = merged.loc[merged["SOV_A3"] == "ESP", "MyValue"].iloc[0]
    year_prt = merged.loc[merged["SOV_A3"] == "PRT", "Year"].iloc[0]

    # Verify that the latest year's values are used: PRT=11, ESP=21, year=2024.
    assert prt_val == 11
    assert esp_val == 21
    assert int(year_prt) == 2024