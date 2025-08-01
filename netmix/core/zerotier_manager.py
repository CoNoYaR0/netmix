import subprocess
import json
import logging

class ZeroTierManager:
    """
    A manager to interact with a local ZeroTier One service.

    This class is a conceptual placeholder. A real implementation would require
    the ZeroTier One client to be installed and running on the host machine.
    It works by calling the `zerotier-cli` command-line tool and parsing
    its JSON output. It will gracefully handle the absence of the CLI tool.
    """
    def __init__(self, cli_path="zerotier-cli"):
        """
        Args:
            cli_path (str): The path to the zerotier-cli executable.
        """
        self.cli_path = cli_path
        self.is_available = True # Assume the CLI is available until a check fails.
        logging.info("ZeroTier Manager initialized.")
        # Perform an initial check to see if the CLI exists.
        self._run_command('--version')

    def _run_command(self, *args):
        """
        Runs a zerotier-cli command and returns the parsed JSON output.

        Returns:
            dict or None: The parsed JSON data, or None if an error occurs.
        """
        if not self.is_available:
            return None

        try:
            command = [self.cli_path, '-j'] + list(args)
            # For the version check, we don't want JSON output.
            if args == ('--version',):
                command = [self.cli_path] + list(args)

            result = subprocess.run(command, capture_output=True, text=True, check=True)

            if args == ('--version',): # Don't try to parse version output as JSON
                logging.info(f"Found ZeroTier version: {result.stdout.strip()}")
                return {"version": result.stdout.strip()}

            return json.loads(result.stdout)
        except FileNotFoundError:
            if self.is_available: # Log the error only once
                logging.error(f"'{self.cli_path}' not found. ZeroTier features will be disabled.")
                self.is_available = False
            return None
        except subprocess.CalledProcessError as e:
            logging.error(f"Command '{' '.join(e.cmd)}' failed with exit code {e.returncode}: {e.stderr}")
            return None
        except json.JSONDecodeError:
            logging.error("Failed to parse JSON output from zerotier-cli.")
            return None

    def get_status(self):
        """
        Gets the status of the local ZeroTier node.
        Equivalent to `zerotier-cli -j info`.
        """
        return self._run_command('info')

    def list_networks(self):
        """
        Lists all networks the local node has joined.
        Equivalent to `zerotier-cli -j listnetworks`.
        """
        return self._run_command('listnetworks')

    def get_network_info(self, network_id):
        """
        Gets detailed information for a specific joined network.
        This is a convenience method that filters the output of list_networks.
        """
        networks = self.list_networks()
        if networks:
            for network in networks:
                if network.get('id') == network_id:
                    return network
        return None

    def list_peers(self):
        """
        Lists all peers known to the local node.
        Equivalent to `zerotier-cli -j listpeers`.
        """
        return self._run_command('listpeers')
