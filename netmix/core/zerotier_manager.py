import subprocess
import json
import logging

class ZeroTierManager:
    """
    A manager to interact with a local ZeroTier One service.

    This class is a conceptual placeholder. A real implementation would require
    the ZeroTier One client to be installed and running on the host machine.
    It works by calling the `zerotier-cli` command-line tool and parsing
    its JSON output.
    """
    def __init__(self, cli_path="zerotier-cli"):
        """
        Args:
            cli_path (str): The path to the zerotier-cli executable.
        """
        self.cli_path = cli_path
        logging.info("ZeroTier Manager initialized.")

    def _run_command(self, *args):
        """
        Runs a zerotier-cli command and returns the parsed JSON output.

        Returns:
            dict or None: The parsed JSON data, or None if an error occurs.
        """
        try:
            # The -j flag is crucial as it provides machine-readable JSON output.
            command = [self.cli_path, '-j'] + list(args)
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except FileNotFoundError:
            logging.error(f"'{self.cli_path}' not found. Is ZeroTier installed and in the system's PATH?")
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
        logging.info("Getting ZeroTier node status...")
        return self._run_command('info')

    def list_networks(self):
        """
        Lists all networks the local node has joined.
        Equivalent to `zerotier-cli -j listnetworks`.
        """
        logging.info("Listing joined ZeroTier networks...")
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
        logging.info("Listing ZeroTier peers...")
        return self._run_command('listpeers')

# Example usage (for demonstration if ZeroTier were installed)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    zt_manager = ZeroTierManager()

    status = zt_manager.get_status()
    if status:
        print("\n--- Node Status ---")
        print(json.dumps(status, indent=2))

    networks = zt_manager.list_networks()
    if networks:
        print("\n--- Joined Networks ---")
        print(json.dumps(networks, indent=2))
