import os
import sys
import time
import shutil
import logging
import psutil
import configparser
import ctypes
from pathlib import Path

# Configure logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("launcher.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

class ETS2Manager:
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.root_dir = Path(__file__).parent

        # 1. Validate paths immediately
        self._validate_paths()

        # 2. Load variables
        self.game_dir = Path(self.config['PATHS']['GameDir'])
        self.launcher_path = Path(self.config['PATHS']['LauncherPath'])
        
        self.bin_dir = self.game_dir / "bin" / "win_x64"
        self.dll_target = self.bin_dir / "steam_api64.dll"
        
        # Load asset paths relative to the script location
        self.dll_original = self.root_dir / self.config['ASSETS']['OriginalDLL']
        self.dll_modified = self.root_dir / self.config['ASSETS']['ModifiedDLL']

        # Load settings
        self.poll_interval = int(self.config['SETTINGS'].get('PollInterval', 2))
        self.grace_period = int(self.config['SETTINGS'].get('LauncherGracePeriod', 15))

    def _show_error_and_open_config(self, message: str):
        """Displays a Windows error message box and opens the configuration file."""
        logging.error(message)
        # 0x10 = Critical Icon, 0x0 = OK Button
        ctypes.windll.user32.MessageBoxW(0, message, "Configuration Error", 0x10 | 0x0)
        os.startfile(self.config_file)
        sys.exit()

    def _validate_paths(self):
        """Ensures all required paths in the config file are valid."""
        # Validate Game Directory
        game_dir_str = self.config['PATHS'].get('GameDir', '').strip()
        if not game_dir_str:
            self._show_error_and_open_config("Please set 'GameDir' in the config file.")
        
        if not Path(game_dir_str).exists():
            self._show_error_and_open_config(f"Game directory not found:\n{game_dir_str}")

        # Validate Launcher Executable
        launcher_str = self.config['PATHS'].get('LauncherPath', '').strip()
        if not launcher_str:
            self._show_error_and_open_config("Please set 'LauncherPath' in the config file.")
        
        if not Path(launcher_str).exists():
            self._show_error_and_open_config(f"TruckersMP executable not found:\n{launcher_str}")

    def _swap_dll(self, source: Path) -> None:
        """Overwrites the game's DLL with the specified source file."""
        try:
            if not source.exists():
                logging.error(f"Source file missing: {source}")
                return
            shutil.copyfile(source, self.dll_target)
            logging.info(f"DLL replaced with: {source.name}")
        except Exception as e:
            logging.error(f"DLL replacement error: {e}")

    def prepare_multiplayer(self) -> None:
        """Prepares the environment for TruckersMP (Original DLL)."""
        logging.info(">>> Preparing for Multiplayer...")
        self._swap_dll(self.dll_original)

    def restore_singleplayer(self) -> None:
        """Restores the environment for Singleplayer (Modified DLL)."""
        logging.info(">>> Restoring Singleplayer configuration...")
        self._swap_dll(self.dll_modified)

    def is_process_running(self, process_name: str) -> bool:
        """Checks if a process is running by name."""
        for proc in psutil.process_iter(['name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def run(self):
        # S1: Setup assets
        self.prepare_multiplayer()
        
        # S2: Launch TruckersMP
        logging.info(f"Launching TruckersMP: {self.launcher_path.name}")
        try:
            # We start the process but don't hold the object reference for polling 
            # because some launcher wrappers exit immediately after spawning a child process.
            psutil.Popen([str(self.launcher_path)], cwd=str(self.launcher_path.parent))
        except Exception as e:
            logging.error(f"Failed to launch TruckersMP: {e}")
            self.restore_singleplayer()
            return

        logging.info("Waiting for game start or launcher closure...")
        
        # S3: Detection Loop
        launcher_name = self.launcher_path.name
        game_started = False
        
        while True:
            # A. Check if the actual game is running
            if self.is_process_running("eurotrucks2.exe"):
                game_started = True
                logging.info("Euro Truck Simulator 2 detected!")
                break
            
            # B. Check if launcher is still open
            # If the launcher closes before the game starts, we start a grace period timer.
            if not self.is_process_running(launcher_name):
                logging.info("Launcher process closed. Waiting for grace period...")
                time.sleep(self.grace_period)

                # Final check after grace period
                if self.is_process_running("eurotrucks2.exe"):
                    game_started = True
                else:
                    logging.warning("Launcher closed and game did not start.")
                break
            
            time.sleep(self.poll_interval)

        if not game_started:
            logging.info("Game start aborted.")
            self.restore_singleplayer()
            return

        # S4: Monitor Game Execution
        logging.info("Monitoring game session...")
        while self.is_process_running("eurotrucks2.exe"):
            time.sleep(self.poll_interval)

        # S5: Cleanup
        logging.info("Game closed.")
        self.restore_singleplayer()
        logging.info("Process complete.")

if __name__ == "__main__":
    try:
        import sys, os

        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        config_path = os.path.join(base_dir, 'config.ini')
        app = ETS2Manager(config_path)
        app.run()
    except Exception as e:
        logging.critical(f"Critical Runtime Error: {e}")
        ctypes.windll.user32.MessageBoxW(0, str(e), "Critical Error", 0x10)
