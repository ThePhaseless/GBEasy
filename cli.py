import logging
import shutil
import sys
from pathlib import Path
from typing import List

from src.functions import (
    copy_contents,
    find_and_get_appid,
    get_7zr,
    get_emu,
    get_emu_tools,
    get_steamless,
    run_process,
    setup_argument_parser,
)
from src.variables import (
    CONFIG_EMU_EXE,
    DOWNLOAD_DIR,
    EMU_PATH,
    INTERFACES_EMU_EXE,
    TOOLS_DIR,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


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


if __name__ == "__main__":
    args = setup_argument_parser()
    overwrite_dll(game_path=Path(args.game_path))
