import requests
from pathlib import Path
from datetime import datetime


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

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises exception for HTTP errors

        # Save the ZIP file
        zip_path = data_dir / "zip" / f"eforms_{month}.zip"
        zip_path.parent.mkdir(exist_ok=True)  # Create zip subdirectory if needed
        with open(zip_path, "wb") as f:
            f.write(response.content)

        print(f"Successfully downloaded eForms zip file for {month}: {zip_path} ({len(response.content)} bytes) \n")
        return zip_path
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading eForms data for {month}: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error occurred: {e}")
        raise


def fetch_eforms_for_range(earliest_month: str, latest_month: str, data_dir: Path):
    """
    Fetch eForms data for a range of months
    
    Args:
        earliest_month: Start month in YYYY-MM format (e.g., "2024-01")
        latest_month: End month in YYYY-MM format (e.g., "2024-12")
        data_dir: Where to save the downloaded files
    """
    
    # Parse start and end dates
    start_date = datetime.strptime(earliest_month, "%Y-%m")
    end_date = datetime.strptime(latest_month, "%Y-%m")
    
    if start_date > end_date:
        raise ValueError("Start month must be before or equal to end month")
    
    print(f"Fetching eForms data from {earliest_month} to {latest_month}...")
    
    downloaded_files = []
    current_date = start_date
    
    while current_date <= end_date:
        month_str = current_date.strftime("%Y-%m")
        try:
            zip_path = fetch_eforms_for_month(month_str, data_dir)
            downloaded_files.append(zip_path)
        except Exception as e:
            print(f"⚠️ Failed to download data for {month_str}: {e}")
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    print(f"✅ Completed download range. Successfully downloaded {len(downloaded_files)} files.")
    return downloaded_files