import argparse
import logging
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import List

import requests

from src.variables import (
    CONFIG_EMU_EXE,
    DOWNLOAD_DIR,
    EMU_PATH,
    EMU_REPO,
    EMU_TOOLS_PATH,
    GITHUB_API_BASE,
    INTERFACES_EMU_EXE,
    SEVENZR_EXE,
    SEVENZR_URL,
    STEAMLESS_REPO,
    TOOLS_DIR,
    TOOLS_REPO,
)


def get_latest_release_asset_url(
    repo: str, asset_name_filter: str | None = None, asset_exact_name: str | None = None
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
    dest_folder.mkdir(parents=True, exist_ok=True)
    if not filename:
        filename = Path(url).name
    dest_path = dest_folder / filename
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
                progress = int(50 * bytes_downloaded / total_size) if total_size else 0
                sys.stdout.write(
                    f"\r[{'=' * progress}{' ' * (50 - progress)}] {bytes_downloaded / (1024 * 1024):.2f} MB / {total_size / (1024 * 1024):.2f} MB"
                )
                sys.stdout.flush()
    sys.stdout.write("\n")  # New line after progress bar
    logging.info(f"Successfully downloaded {dest_path}")
    return dest_path


def extract_archive(archive_path: Path, extract_to_folder: Path):
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
            command = [
                str(sevenzr_path),
                "x",
                str(archive_path),
                f"-o{str(extract_to_folder)}",
                "-aoa",
            ]
            run_process(command)
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


def find_and_get_appid(search_path: Path) -> str:
    """Finds steam_appid.txt or prompts user for AppID."""

    app_id_file = None
    for path in search_path.rglob("steam_appid.txt"):
        if path.is_file():
            app_id_file = path
            break

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

    logging.info("Could not find steam_appid.txt")
    while True:
        appid = input("Please enter the Steam AppID: ").strip()
        if not appid.isdigit():
            logging.warning(f"Invalid AppID entered: {appid}. Please try again.")
            continue
        return appid


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
    # !TODO
    # parser.add_argument(
    #     "--client",
    #     action="store_true",
    #     help="Instead of overwriting the dlls, use the Steam Goldberg Client to inject emulator into the app.",
    # )
    args = parser.parse_args()
    return args


def get_steamless():
    logging.info("--- Processing Steamless (Download Only) ---")
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
    logging.info("--- Processing GBE Fork Emulator ---")
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
    emu_dll_dir = emu_extract_path / "release" / "experimental" / "x64"

    if not emu_dll_dir.exists():
        logging.error(
            f"Could not find {emu_dll_dir} folder in extracted GBE Fork Emulator."
        )
        sys.exit(1)
    return emu_dll_dir


def get_emu_tools():
    logging.info("--- Processing GBE Fork Tools ---")

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
    if not CONFIG_EMU_EXE.exists():
        logging.error(f"Generator executable not found at {CONFIG_EMU_EXE}. Exiting.")
        sys.exit(1)


def get_7zr():
    if SEVENZR_EXE.exists():
        logging.info(f"7zr.exe already exists at {SEVENZR_EXE}. Skipping download.")
        return
    logging.info("7zr.exe not found. Downloading...")
    if not download_file(SEVENZR_URL, DOWNLOAD_DIR):
        logging.error("Failed to download 7zr.exe. Exiting.")
        sys.exit(1)


def run_process(
    command: List[str],
    print_errors: bool = True,
    show_output: bool = False,
):
    logging.info(f"Running: {' '.join(command)}")
    exception = None
    try:
        subprocess.run(
            command,
            stdout=None if show_output else subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        exception = e
        if print_errors:
            logging.error(f"Command failed with return code {e.returncode}.")
            if e.stdout:
                logging.error(f"Output:\n{bytes(e.stdout).decode('utf-8')}")
            if e.stderr:
                logging.error(f"Error Output:\n{bytes(e.stderr).decode('utf-8')}")
    except Exception as e:
        exception = e
        if print_errors:
            logging.error(
                f"An unexpected error occurred while running the generator: {e}"
            )

    if exception:
        raise exception


def overwrite_dll(game_path: Path) -> None:
    logging.info("--- Determining Steam AppID ---")
    app_id = find_and_get_appid(game_path)

    # --- Ensure working directories exist ---
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Download and setup Tools ---
    get_7zr()  # aka 7zip cli
    get_emu_tools()
    get_emu()
    get_steamless()

    # Decrypt .exe files with steamless
    logging.info("--- Decrypting .exe files with Steamless ---")
    steamless_cli = TOOLS_DIR / "steamless" / "steamless.cli.exe"
    if not steamless_cli.exists():
        logging.error("steamless.cli.exe not found. Exiting.")
        sys.exit(1)

    exe_list: List[Path] = []
    for steam_dll in game_path.rglob("*.exe"):
        if steam_dll.is_file():
            exe_list.append(steam_dll)

    if not exe_list or len(exe_list) == 0:
        logging.error("No .exe files found in the game directory. Exiting.")
        sys.exit(1)

    logging.info("Trying to decrypt files")
    for exe in exe_list:
        try:
            run_process([str(steamless_cli), "--quiet", str(exe)], False)
            logging.info(f"{exe} decrypted successfully.")
        except Exception:
            pass
        else:
            logging.info(f"Decrypted {exe.name} successfully, replacing...")
            shutil.copyfile(exe, exe.with_suffix(".exe.bak"))
            shutil.move(exe.with_suffix(".exe.unpacked.exe"), exe)

    # --- Find steam_api64.dll ---
    logging.info("--- Locating steam_api64.dll ---")
    steam_dlls: List[Path] = []
    for steam_dll in game_path.rglob("steam_api64.dll"):
        # Check if path contains word crack or original
        if "crack" in str(steam_dll).lower() or "original" in str(steam_dll).lower():
            logging.info(f"Skipping {steam_dll} as it is a crack or original version.")
            continue
        if steam_dll.is_file():
            logging.info(f"Found steam_api64.dll at {steam_dll}")
            steam_dlls.append(steam_dll)
            shutil.copy(
                steam_dll, steam_dll.with_suffix(".dll.bak")
            )  # Rename original dll
    if not steam_dlls:
        logging.error("steam_api64.dll not found in src directory. Exiting.")
        sys.exit(1)

    # --- Call generate_emu_config ---
    logging.info("--- Generating Emulator Config ---")
    command = [str(CONFIG_EMU_EXE), "-cve", "-token", app_id]
    run_process(command, show_output=True)

    # --- Copy Generator Output ---
    logging.info("--- Copying Emulator Config Files ---")
    for steam_dll in steam_dlls:
        shutil.copytree(
            Path("output") / app_id,
            steam_dll.parent,
            dirs_exist_ok=True,
        )

    # --- Generate interfaces ---
    logging.info("--- Generating Interfaces ---")
    for steam_dll in steam_dlls:
        command = [str(INTERFACES_EMU_EXE), str(steam_dll)]
        try:
            run_process(command, print_errors=False)
        except Exception:
            logging.error(f"Failed to generate interfaces for {steam_dll}")
            continue

        shutil.copyfile(
            "steam_interfaces.txt",
            steam_dll.parent / "steam_settings",
        )
        # --- Copy Experimental Files ---
        logging.info("--- Copying Interfaces ---")
        if not copy_contents(EMU_PATH, steam_dll.parent):
            logging.error("Failed to copy files. Exiting.")
            sys.exit(1)

    logging.info("--- Script finished successfully! ---")
