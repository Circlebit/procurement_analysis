from src.fetch_data import fetch_eforms_for_range
from pathlib import Path


def main():
    print("Procurement Data Fetcher \n")

    data_path = Path("data")

    fetch_eforms_for_range (
        earliest_month = "2024-09",
        latest_month = "2024-11",
        data_dir=data_path
    )

    print("🏁 Data fetching complete \n")


if __name__ == "__main__":
    main()
