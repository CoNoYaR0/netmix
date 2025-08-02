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

        Args:
            cli_path (str, optional): A direct path to the zerotier-cli executable.
                                      If None, it will be auto-detected.
        """
        self.cli_path = cli_path or self._find_cli()
        self.is_available = self.cli_path is not None

        if self.is_available:
            logging.info(f"ZeroTier Manager initialized using executable at: {self.cli_path}")
        else:
            logging.error("Could not find zerotier-cli. ZeroTier features will be disabled.")

    def _find_cli(self):
        """
        Tries to find the zerotier-cli executable in a robust way.
        1. Checks for a ZEROTIER_CLI_PATH environment variable.
        2. Checks if 'zerotier-cli' is in the system's PATH.
        3. Checks the default Windows installation directory.
        """
        # 1. Check environment variable
        env_path = os.environ.get('ZEROTIER_CLI_PATH')
        if env_path and os.path.exists(env_path):
            logging.info(f"Found zerotier-cli via ZEROTIER_CLI_PATH environment variable: {env_path}")
            return env_path

        # 2. Check system PATH
        if shutil.which('zerotier-cli'):
            logging.info("Found zerotier-cli in system PATH.")
            return 'zerotier-cli'

        # 3. Check default Windows installation path
        win_path = r"C:\ProgramData\ZeroTier\One\zerotier-cli.exe"
        if os.name == 'nt' and os.path.exists(win_path):
            logging.info(f"Found zerotier-cli at default Windows path: {win_path}")
            return win_path

        return None

    def _run_command(self, *args):
        """
        Runs a zerotier-cli command and returns the parsed JSON output.
        """
        if not self.is_available:
            return None

        try:
            command = [self.cli_path, '-j'] + list(args)
            result = subprocess.run(command, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logging.error(f"Error executing or parsing zerotier-cli command: {e}")
            return None

    def get_status(self):
        return self._run_command('info')

    def list_networks(self):
        return self._run_command('listnetworks')

    def list_peers(self):
        return self._run_command('listpeers')
