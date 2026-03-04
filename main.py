from okavango.data_manager import download_all_datasets

if __name__ == "__main__":
    paths = download_all_datasets()
    print("Downloaded:")
    for k, v in paths.items():
        print(f"- {k}: {v}")