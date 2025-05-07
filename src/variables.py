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
EMU_PATH = TOOLS_DIR / "gbe_fork_emu" / "release" / "experimental" / "x64"
STEAMLESS_PATH = TOOLS_DIR / "steamless"

SEVENZR_EXE = DOWNLOAD_DIR / "7zr.exe"
CONFIG_EMU_EXE = EMU_TOOLS_PATH / "generate_emu_config" / "generate_emu_config.exe"
# tools\gbe_fork_emu\release\tools\generate_interfaces\generate_interfaces_x64.exe
INTERFACES_EMU_EXE = (
    TOOLS_DIR
    / "gbe_fork_emu"
    / "release"
    / "tools"
    / "generate_interfaces"
    / "generate_interfaces_x64.exe"
)
