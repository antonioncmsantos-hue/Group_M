from okavango.data_manager import download_all_datasets
import subprocess
import sys

if __name__ == "__main__":
    paths = download_all_datasets()
    for k, v in paths.items():
        print(f"- {k}: {v}")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py"],
        check=True,
    )