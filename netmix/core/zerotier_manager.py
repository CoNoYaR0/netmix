import subprocess
import json
import logging
import os
import shutil

class ZeroTierManager:
    """
    A manager to interact with a local ZeroTier One service.
    This class attempts to find the zerotier-cli executable automatically
    and will gracefully handle its absence.
    """
    def __init__(self, cli_path=None):
        """
        Initializes the manager and finds the zerotier-cli path.
        """
        self.cli_path = cli_path or self._find_cli()
        self.is_available = self.cli_path is not None

        if self.is_available:
            logging.info(f"ZeroTier Manager initialized using executable at: {self.cli_path}")
        else:
            logging.warning("Could not find zerotier-cli. ZeroTier features will be disabled.")

    def _find_cli(self):
        """
        Tries to find the absolute path to the zerotier-cli executable.
        1. Checks for a ZEROTIER_CLI_PATH environment variable.
        2. Checks the default Windows installation directory.
        3. Uses shutil.which to search the system's PATH.
        """
        # 1. Check environment variable for a direct path.
        env_path = os.environ.get('ZEROTIER_CLI_PATH')
        if env_path and os.path.exists(env_path):
            logging.info(f"Found zerotier-cli via ZEROTIER_CLI_PATH: {env_path}")
            return env_path

        # 2. Check default Windows installation path.
        if os.name == 'nt':
            win_path = r"C:\ProgramData\ZeroTier\One\zerotier-cli.exe"
            if os.path.exists(win_path):
                logging.info(f"Found zerotier-cli at default Windows path: {win_path}")
                return win_path

        # 3. Check system PATH using shutil.which (more reliable).
        # Explicitly check for .exe on windows.
        executable = 'zerotier-cli.exe' if os.name == 'nt' else 'zerotier-cli'
        which_path = shutil.which(executable)
        if which_path:
            logging.info(f"Found zerotier-cli in system PATH: {which_path}")
            return which_path

        return None

    def _run_command(self, *args):
        """
        Runs a zerotier-cli command and returns the parsed JSON output.
        """
        if not self.is_available:
            return None

        try:
            command = [self.cli_path, '-j'] + list(args)
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
            # Catch FileNotFoundError here as a final fallback.
            logging.error(f"Error executing command with '{self.cli_path}': {e}")
            self.is_available = False # Disable for future calls if it fails once.
            return None

    def get_status(self):
        return self._run_command('info')

    def list_networks(self):
        return self._run_command('listnetworks')

    def list_peers(self):
        return self._run_command('listpeers')
