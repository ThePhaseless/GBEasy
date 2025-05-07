import logging
from pathlib import Path

from src.functions import (
    overwrite_dll,
    setup_argument_parser,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


if __name__ == "__main__":
    args = setup_argument_parser()
    overwrite_dll(game_path=Path(args.game_path))
