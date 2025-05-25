from src.fetch_data import fetch_eforms_for_month
from pathlib import Path


def main():
    print("Procurement Data Fetcher")

    month = "2024-12"
    data_path = Path("data")

    fetch_eforms_for_month(month, data_path)
    print(f"✅ Successfully downloaded eFo‚rms zip file for {month}")


if __name__ == "__main__":
    main()
