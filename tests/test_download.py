# Imports for type annotations, path handling, and the data manager module being tested.
from __future__ import annotations

from pathlib import Path
import types

import okavango.data_manager as dm


# Mock HTTP response class used to simulate requests.get() responses during testing, without making real network calls.
class DummyResponse:
    def __init__(self, content: bytes = b"col1,col2\n1,2\n"):
        self.content = content

    def raise_for_status(self) -> None:
        return None


def test_download_all_datasets_writes_files(tmp_path, monkeypatch):
    # 1) Ensure files are written to a temporary directory (not the real downloads folder)
    monkeypatch.setattr(dm, "DOWNLOADS_DIR", tmp_path / "downloads")

    ## 2) Reduce DATASETS to a simple, deterministic case with two known example URLs
    monkeypatch.setattr(
        dm,
        "DATASETS",
        {
            "red_list_index": "https://example.com/red-list-index.csv",
            "share_degraded_land": "https://example.com/share-degraded-land.csv",
        },
    )

    # 3) Simulate requests.get without internet access by replacing it with a fake function
    def fake_get(url: str):
        return DummyResponse(content=b"Entity,Code,Year,Value\nPortugal,PRT,2024,1\n")

    monkeypatch.setattr(dm.requests, "get", fake_get)

    # 4) Run the function under test
    paths = dm.download_all_datasets()

    # 5) Validate outputs
    assert set(paths.keys()) == {"red_list_index", "share_degraded_land"}
    for name, path in paths.items():
        assert isinstance(path, Path)
        assert path.exists()
        assert path.name == f"{name}.csv"
        assert path.read_text().startswith("Entity,Code,Year,Value")