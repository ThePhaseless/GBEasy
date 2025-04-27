import argparse
import logging
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import requests

from src.variables import (
    DOWNLOAD_DIR,
    EMU_REPO,
    EMU_TOOLS_PATH,
    GENERATOR_EXE,
    GITHUB_API_BASE,
    SEVENZR_EXE,
    SEVENZR_URL,
    STEAMLESS_REPO,
    TOOLS_DIR,
    TOOLS_REPO,
)


def get_latest_release_asset_url(
    repo, asset_name_filter=None, asset_exact_name=None
) -> str | None:
    """Fetches the download URL for a specific asset from the latest GitHub release."""
    api_url = f"{GITHUB_API_BASE}/{repo}/releases/latest"
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        release_data = response.json()
        assets = release_data.get("assets", [])

        if not assets:
            logging.error(f"No assets found in the latest release for {repo}")
            return None

        for asset in assets:
            asset_name = asset.get("name", "")
            if asset_exact_name and asset_name == asset_exact_name:
                logging.info(f"Found exact match asset '{asset_name}' for {repo}")
                return asset.get("browser_download_url")
            elif (
                asset_name_filter
                and asset_name_filter in asset_name
                and asset_name.endswith((".zip", ".7z"))
            ):
                # Prioritize zip if multiple matches containing filter exist and no exact match specified
                # Or just return the first match if only filter is used
                logging.info(
                    f"Found filtered asset '{asset_name}' for {repo} using filter '{asset_name_filter}'"
                )
                # Simple logic: return the first match found containing the filter
                # More complex logic could be added here if needed (e.g. prefer .zip)
                return asset.get("browser_download_url")

        # If only a filter was provided and no match found after checking all
        if asset_name_filter and not asset_exact_name:
            logging.error(
                f"No asset containing '{asset_name_filter}' found in the latest release for {repo}"
            )
            return None
        # If exact name was provided and not found
        elif asset_exact_name:
            logging.error(
                f"Asset '{asset_exact_name}' not found in the latest release for {repo}"
            )
            return None
        # If no filter/name provided, try to find a zip or 7z
        else:
            for asset in assets:
                asset_name = asset.get("name", "")
                if asset_name.endswith(".zip") or asset_name.endswith(".7z"):
                    logging.info(
                        f"Found generic archive asset '{asset_name}' for {repo}"
                    )
                    return asset.get("browser_download_url")
            logging.error(
                f"No suitable archive (.zip or .7z) found in the latest release for {repo}"
            )
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching release info for {repo}: {e}")
        return None
    except Exception as e:
        logging.error(
            f"An unexpected error occurred while fetching release info for {repo}: {e}"
        )
        return None


def download_file(url: str, dest_folder: Path, filename: str | None = None):
    """Downloads a file from a URL to a destination folder."""
    if not url:
        return None
    dest_folder.mkdir(parents=True, exist_ok=True)
    if not filename:
        filename = Path(url).name
    dest_path = dest_folder / filename
    try:
        logging.info(f"Downloading {filename} from {url}...")
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))
            block_size = 8192  # 8KB
            bytes_downloaded = 0
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=block_size):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    # Basic progress indication
                    progress = (
                        int(50 * bytes_downloaded / total_size) if total_size else 0
                    )
                    sys.stdout.write(
                        f"\r[{'=' * progress}{' ' * (50 - progress)}] {bytes_downloaded / (1024 * 1024):.2f} MB / {total_size / (1024 * 1024):.2f} MB"
                    )
                    sys.stdout.flush()
        sys.stdout.write("\n")  # New line after progress bar
        logging.info(f"Successfully downloaded {dest_path}")
        return dest_path
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading {url}: {e}")
        if dest_path.exists():
            os.remove(dest_path)  # Clean up partial download
        return None
    except Exception as e:
        logging.error(f"An error occurred during download: {e}")
        if dest_path.exists():
            os.remove(dest_path)
        return None


def extract_archive(archive_path, extract_to_folder):
    """Extracts a .zip or .7z archive."""
    if not archive_path or not archive_path.exists():
        logging.error(f"Archive path does not exist: {archive_path}")
        return False
    extract_to_folder.mkdir(parents=True, exist_ok=True)
    logging.info(f"Extracting {archive_path.name} to {extract_to_folder}...")
    try:
        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(extract_to_folder)
            logging.info("Successfully extracted zip archive.")
            return True
        elif archive_path.suffix == ".7z":
            # Use 7zr to extract .7z files
            sevenzr_path = Path(DOWNLOAD_DIR) / "7zr.exe"
            if not sevenzr_path.exists():
                logging.error("7zr.exe not found. Cannot extract .7z files.")
                return False
            subprocess.run(
                [
                    str(sevenzr_path),
                    "x",
                    str(archive_path),
                    f"-o{extract_to_folder}",
                    "-aoa",
                ],
                check=True,
            )
            logging.info("Successfully extracted 7z archive.")
            return True
        else:
            logging.error(f"Unsupported archive type: {archive_path.suffix}")
            return False
    except zipfile.BadZipFile:
        logging.error(f"Error: Bad Zip file: {archive_path}")
        return False

    except Exception as e:
        logging.error(f"Failed to extract {archive_path}: {e}")
        return False


def find_file_recursive(search_path, filename):
    """Recursively finds the first occurrence of a file and returns its containing directory."""
    logging.info(f"Searching for {filename} in {search_path}")
    for root, dirs, files in os.walk(search_path):
        if filename in files:
            found_dir = Path(root)
            logging.info(f"Found {filename} in: {found_dir}")
            return found_dir / filename
    logging.warning(f"{filename} not found in {search_path} or its subdirectories.")
    return None


def find_and_get_appid(search_path: Path):
    """Finds steam_appid.txt or prompts user for AppID."""
    app_id_file = find_file_recursive(search_path, "steam_appid.txt")
    if app_id_file and app_id_file.is_file():
        logging.info(f"Found {app_id_file}")
        try:
            with open(app_id_file, "r") as f:
                appid = f.read().strip()
            if appid.isdigit():
                logging.info(f"Read AppID: {appid} from file {search_path}.")
                return appid
            else:
                logging.warning(
                    f"Content of {app_id_file} ('{appid}') is not a valid AppID."
                )
        except Exception as e:
            logging.warning(f"Could not read {app_id_file}: {e}")

    while True:
        try:
            appid = input("Please enter the Steam AppID: ").strip()
            if not appid.isdigit():
                logging.warning(f"Invalid AppID entered: {appid}. Please try again.")
                continue
            return appid
        except KeyboardInterrupt:
            logging.error("User interrupted AppID input.")
            return None
        except EOFError:
            logging.error("EOF detected during AppID input.")
            return None


def copy_contents(src_dir: Path, dest_dir: Path):
    """Copies contents of src_dir to dest_dir, overwriting existing files/dirs."""
    if not src_dir.is_dir():
        logging.error(f"Source directory for copy does not exist: {src_dir}")
        return False
    if not dest_dir.is_dir():
        logging.error(f"Destination directory for copy does not exist: {dest_dir}")
        return False

    logging.info(f"Copying contents from {src_dir} to {dest_dir} (overwriting)...")
    try:
        # dirs_exist_ok=True prevents error if subdirs already exist
        shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
        logging.info("Successfully copied contents.")
        return True
    except Exception as e:
        logging.error(f"Failed to copy contents: {e}")
        return False


def setup_argument_parser():
    parser = argparse.ArgumentParser(
        description="Automated game setup tool using GBE Fork and Steamless."
    )
    parser.add_argument(
        "game_path",
        help="Path to the game's installation directory.",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete downloaded and extracted tool files after script completion.",
    )
    args = parser.parse_args()
    return args


def get_steamless():
    logging.info("--- Step 3: Processing Steamless (Download Only) ---")
    steamless_url = get_latest_release_asset_url(
        STEAMLESS_REPO, asset_name_filter=".zip"
    )  # Or specify exact name if known
    if not steamless_url:
        logging.warning("Failed to find Steamless release. Continuing without it.")
        # Decide if this is critical or optional for the user's *actual* goal.
        # For now, let's just continue without it.
        return

    logging.info(f"Downloading Steamless from {steamless_url}...")

    # Check if already downloaded
    steamless_archive = DOWNLOAD_DIR / Path(steamless_url).name
    if steamless_archive.exists():
        logging.info(
            f"Latest Steamless release already downloaded: {steamless_archive.name}. Skipping download."
        )
    else:
        # Download if not already present
        steamless_archive = download_file(steamless_url, DOWNLOAD_DIR)
    steamless_extract_path = TOOLS_DIR / "steamless"
    if not steamless_archive or not extract_archive(
        steamless_archive, steamless_extract_path
    ):
        logging.warning(
            "Failed to download or extract Steamless. Continuing without it."
        )


def get_emu():
    logging.info("--- Step 2: Processing GBE Fork Emulator ---")
    emu_url = get_latest_release_asset_url(
        EMU_REPO, asset_exact_name="emu-win-release.7z"
    )
    if not emu_url:
        logging.error("Failed to find GBE Fork Emulator release. Exiting.")
        sys.exit(1)
    emu_archive = download_file(emu_url, DOWNLOAD_DIR)
    emu_extract_path = TOOLS_DIR / "gbe_fork_emu"
    if not emu_archive or not extract_archive(emu_archive, emu_extract_path):
        logging.error("Failed to download or extract GBE Fork Emulator. Exiting.")
        sys.exit(1)
    # Find the 'experimental' folder - might be nested
    emu_dll_dir = emu_extract_path / "release" / "experimental" / "x64"

    if not emu_dll_dir.exists():
        logging.error(
            f"Could not find {emu_dll_dir} folder in extracted GBE Fork Emulator."
        )
        # Decide if this is fatal or just a warning? Let's make it fatal for now.
        sys.exit(1)
    return emu_dll_dir


def get_emu_tools():
    logging.info("--- Step 1: Processing GBE Fork Tools ---")

    tools_url = get_latest_release_asset_url(TOOLS_REPO, asset_name_filter="win")
    if not tools_url:
        logging.error("Failed to find GBE Fork Tools release. Exiting.")
        sys.exit(1)
    tools_archive = DOWNLOAD_DIR / Path(tools_url).name

    if not tools_archive.exists():
        tools_archive = download_file(tools_url, DOWNLOAD_DIR)
    else:
        logging.info(
            f"Latest release already downloaded: {tools_archive.name}. Skipping download."
        )
    if not extract_archive(tools_archive, EMU_TOOLS_PATH):
        logging.error("Failed to extract GBE Fork Tools. Exiting.")
        sys.exit(1)
    if not GENERATOR_EXE.exists():
        logging.error(f"Generator executable not found at {GENERATOR_EXE}. Exiting.")
        sys.exit(1)


def get_7zr():
    if not SEVENZR_EXE.exists():
        logging.info("7zr.exe not found. Downloading...")
        if not download_file(SEVENZR_URL, DOWNLOAD_DIR):
            logging.error("Failed to download 7zr.exe. Exiting.")
            sys.exit(1)
