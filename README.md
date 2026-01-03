# DLC Toggle for ETS2

A small utility to swap the `steam_api64.dll` in Euro Truck Simulator 2 to support multiplayer via TruckersMP.

Note: The Steam API DLL (original and modified) is NOT distributed in this repo.
DO NOT commit the DLL to the repository.

## Overview

This tool acts as a wrapper for the TruckersMP launcher. It automatically swaps the `steam_api64.dll` file depending on the context:
1. **Launch:** Backs up the modified DLL and installs the authentic Steam DLL.
2. **Monitor:** Launches TruckersMP and waits for the game (`eurotrucks2.exe`) to start.
3. **Restore:** Once the game closes, it automatically restores the modified DLL for Singleplayer use.

## Prerequisites

- Windows 10/11
- Python 3.x (if running from source)
- `psutil` library

```bash
pip install psutil
```

## Usage

**DLL Files** Note: DLL files are NOT included for licensing reasons.
- Place the *authentic* Steam API DLL in `assets/original_steam_api64.dll`
- Place your *modified* API DLL in `assets/modified_steam_api64.dll`

Run the script with the Python interpreter:

```bash
python main.py
```

The script logs to `launcher.log` and prints status to the console.

## Notes & Tips

- The script uses Windows-specific APIs for message boxes; it is intended for Windows only.
- Always backup files before running; the script attempts to restore state after the game exits.
