import logging
import shutil
import subprocess
import sys
from pathlib import Path

from src.functions import (
    copy_contents,
    find_and_get_appid,
    find_file_recursive,
    get_7zr,
    get_emu,
    get_emu_tools,
    get_steamless,
    setup_argument_parser,
)
from src.variables import (
    DOWNLOAD_DIR,
    EMU_PATH,
    EMU_TOOLS_PATH,
    GENERATOR_EXE,
    TOOLS_DIR,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    args = setup_argument_parser()
    game_path = Path(args.game_path)

    logging.info("--- Determining Steam AppID ---")
    app_id = find_and_get_appid(game_path)
    if not app_id:
        logging.error("Failed to get Steam AppID. Exiting.")
        sys.exit(1)

    # --- Ensure working directories exist ---
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Download and setup Tools ---
    get_7zr()  # aka 7zip cli
    get_emu_tools()
    get_emu()
    get_steamless()

    # --- Step 2: Find steam_api64.dll ---
    logging.info("--- Locating steam_api64.dll ---")
    steam_api_dir = None

    if not (dll_path := find_file_recursive(game_path, "steam_api64.dll")):
        logging.error(f"Could not find steam_api64.dll within {game_path}. Exiting.")
        sys.exit(1)
    else:
        steam_api_dir = dll_path.parent

    # --- Step 4: Call generate_emu_config ---
    logging.info("--- Generating Emulator Config ---")
    generator_output_dir = EMU_TOOLS_PATH / "output"  # Default output dir for the tool
    command = [str(GENERATOR_EXE), "-cve", "-token", app_id]
    logging.info(f"Running: \n{' '.join(command)}")
    try:
        # Run from the directory containing the exe to handle relative paths correctly
        process = subprocess.run(
            command,
            check=True,
            cwd=EMU_TOOLS_PATH,
        )
        if process.stderr:
            logging.warning("Generator errors/warnings\n")
            sys.exit(1)
        logging.info("generate_emu_config executed successfully.")
    except FileNotFoundError:
        logging.error(
            f"Generator executable not found at {GENERATOR_EXE}. Ensure it was extracted correctly."
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logging.error(f"generate_emu_config failed with return code {e.returncode}.")
        logging.error(f"Output:\n{e.stdout}")
        logging.error(f"Error Output:\n{e.stderr}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred while running the generator: {e}")
        sys.exit(1)

    # --- Step 7: Copy Generator Output ---
    logging.info("--- Copying Generated Files ---")
    generator_appid_output_dir = generator_output_dir / app_id
    if not generator_appid_output_dir.is_dir():
        logging.error(
            f"Generator output directory '{generator_appid_output_dir}' not found. Check generator execution."
        )
        sys.exit(1)
    if not copy_contents(generator_appid_output_dir, steam_api_dir):
        logging.error("Failed to copy generator output files. Exiting.")
        sys.exit(1)

    # --- Step 8: Copy Experimental Files ---
    logging.info("--- Copying emulator Files ---")
    if not copy_contents(EMU_PATH, steam_api_dir):
        logging.error("Failed to copy files. Exiting.")
        sys.exit(1)

    # --- Cleanup ---
    if args.cleanup:
        logging.info("--- Cleaning up downloaded and extracted files ---")
        try:
            if DOWNLOAD_DIR.exists():
                shutil.rmtree(DOWNLOAD_DIR)
                logging.info(f"Removed {DOWNLOAD_DIR}")
            if TOOLS_DIR.exists():
                shutil.rmtree(TOOLS_DIR)
                logging.info(f"Removed {TOOLS_DIR}")
        except Exception as e:
            logging.warning(f"Error during cleanup: {e}")

    logging.info("--- Script finished successfully! ---")


if __name__ == "__main__":
    main()
