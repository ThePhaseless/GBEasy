# GBEasy

Generate and apply Goldberg Emulator on a given steam app.

## Usage

### From source
1. [Download `uv`](https://docs.astral.sh/uv/getting-started/installation/)
2. Clone the repository
3. Run `uv sync`
4. Run `uv run cli.py <path to game>`

### From binary
1. Click on [Actions](https://github.com/ThePhaseless/GBEasy/actions)
2. Choose the latest build
3. In Artifacts, download `cli`
4. Extract the archive and run `gbeasy.exe <path to game>`


## Features

- Downloads the latest Goldberg Emulator build.
- Downloads the latest Steamless release (optional, download only for now).
- Copies Goldberg Emulator files to the game directory.
- Option to clean up downloaded files after completion.

## TODO

- Implement automatic Steam AppID lookup by game name if `steam_appid.txt` is not found.
- Integrate Steamless usage to automatically unpack SteamStub protected executables.
