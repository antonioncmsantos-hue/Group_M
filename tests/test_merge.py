from __future__ import annotations

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from okavango.data_manager import merge_world_with_dataset


def test_merge_world_with_dataset_uses_latest_year():
    # world map fake (geopandas à esquerda) com SOV_A3 como no vosso Natural Earth
    world = gpd.GeoDataFrame(
        {
            "SOV_A3": ["PRT", "ESP"],
            "ADMIN": ["Portugal", "Spain"],
            "geometry": [Point(0, 0), Point(1, 1)],
        },
        geometry="geometry",
        crs="EPSG:4326",
    )

    # df OWID fake com 2 anos (latest = 2024)
    df = pd.DataFrame(
        {
            "Entity": ["Portugal", "Portugal", "Spain", "Spain"],
            "Code": ["PRT", "PRT", "ESP", "ESP"],
            "Year": [2023, 2024, 2023, 2024],
            "MyValue": [10, 11, 20, 21],
        }
    )

    merged = merge_world_with_dataset(world=world, df=df, value_column="MyValue")

    # valida colunas e valores do último ano
    assert "MyValue" in merged.columns
    assert "Year" in merged.columns

    prt_val = merged.loc[merged["SOV_A3"] == "PRT", "MyValue"].iloc[0]
    esp_val = merged.loc[merged["SOV_A3"] == "ESP", "MyValue"].iloc[0]
    year_prt = merged.loc[merged["SOV_A3"] == "PRT", "Year"].iloc[0]

    assert prt_val == 11
    assert esp_val == 21
    assert int(year_prt) == 2024