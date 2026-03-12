from __future__ import annotations

from pathlib import Path

import okavango.data_manager as dm


class DummyResponse:
    """
    Minimal mock response object used to simulate ``requests.get``.

    Parameters
    ----------
    content : bytes, optional
        Raw byte content to expose through the ``content`` attribute,
        by default ``b"col1,col2\\n1,2\\n"``.

    Notes
    -----
    This helper mimics only the small subset of the real ``requests.Response``
    interface required by the tested download logic.
    """

    def __init__(self, content: bytes = b"col1,col2\n1,2\n"):
        self.content = content

    def raise_for_status(self) -> None:
        """
        Mimic a successful HTTP response.

        Returns
        -------
        None
            This mock method does nothing because the simulated response is
            always considered successful.
        """
        return None


def test_download_all_datasets_writes_files(tmp_path, monkeypatch):
    """
    Verify that all configured datasets are downloaded and written to disk.

    This test replaces the real dataset configuration with a small deterministic
    test case and mocks ``requests.get`` so no real HTTP requests are made.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest temporary directory fixture used to isolate filesystem writes.
    monkeypatch : pytest.MonkeyPatch
        Fixture used to replace global variables and functions during the test.

    Returns
    -------
    None
        This test performs assertions and does not return a value.

    Notes
    -----
    The test checks that:
    - the expected dataset keys are returned,
    - files are created in the temporary downloads folder,
    - each file has the expected filename,
    - the written file content matches the mocked CSV payload.
    """
    # Use a temporary downloads directory to avoid touching real project files.
    downloads_dir = tmp_path / "downloads"

    # Replace the production dataset list with a deterministic test version.
    monkeypatch.setattr(
        dm,
        "DATASETS",
        {
            "red_list_index": "https://example.com/red-list-index.csv",
            "share_degraded_land": "https://example.com/share-degraded-land.csv",
        },
    )

    # Mock requests.get so the test does not depend on internet access.
    def fake_get(url: str, timeout: int = 30):
        return DummyResponse(
            content=b"Entity,Code,Year,Value\nPortugal,PRT,2024,1\n"
        )

    monkeypatch.setattr(dm.requests, "get", fake_get)

    # Run the function under test using the temporary directory.
    paths = dm.download_all_datasets(downloads_dir=downloads_dir)

    assert set(paths.keys()) == {"red_list_index", "share_degraded_land"}

    # Confirm that each expected file was written correctly.
    for name, path in paths.items():
        assert isinstance(path, Path)
        assert path.exists()
        assert path.parent == downloads_dir
        assert path.name == f"{name}.csv"
        assert path.read_text().startswith("Entity,Code,Year,Value")