import requests
from pathlib import Path


def fetch_eforms_for_month(month: str, data_dir: Path):
    """
    Fetch eForms data zip file for a given month (format: YYYY-MM)

    Args:
        month: Month in YYYY-MM format (e.g., "2024-12")
        data_dir: Where to save the downloaded files
    """

    url = "https://oeffentlichevergabe.de/api/notice-exports"
    params = {"pubMonth": month, "format": "eforms.zip"}

    # Create data directory
    data_dir.mkdir(exist_ok=True)

    print(f"Fetching eForms data for {month}...")

    response = requests.get(url, params=params)
    response.raise_for_status()  # Raises exception for HTTP errors

    # Save the ZIP file
    zip_path = data_dir / f"eforms_{month}.zip"
    with open(zip_path, "wb") as f:
        f.write(response.content)

    print(f"Downloaded: {zip_path} ({len(response.content)} bytes)")
    return zip_path
