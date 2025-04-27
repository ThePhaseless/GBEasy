# --- Configuration ---
from pathlib import Path

GITHUB_API_BASE = "https://api.github.com/repos"
TOOLS_REPO = "Detanup01/gbe_fork_tools"
EMU_REPO = "Detanup01/gbe_fork"
STEAMLESS_REPO = "atom0s/Steamless"
SEVENZR_URL = "https://www.7-zip.org/a/7zr.exe"

DOWNLOAD_DIR = Path("./tools/downloads")
TOOLS_DIR = Path("./tools")

EMU_TOOLS_PATH = TOOLS_DIR / "gbe_fork_tools"
EMU_PATH = TOOLS_DIR / "gbe_fork_emu"
STEAMLESS_PATH = TOOLS_DIR / "steamless"

SEVENZR_EXE = TOOLS_DIR / "7zr.exe"
GENERATOR_EXE = EMU_TOOLS_PATH / "generate_emu_config" / "generate_emu_config.exe"
