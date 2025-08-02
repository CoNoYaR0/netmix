import psutil
import socket

def get_active_interfaces():
    """
    Identifies all active, non-loopback network interfaces with an IPv4 address.

    Returns:
        A dictionary where keys are interface names and values are their IPv4 addresses.
        e.g., {'Wi-Fi': '192.168.1.100', 'Ethernet': '192.168.1.101'}
    """
    active_interfaces = {}
    if_stats = psutil.net_if_stats()
    if_addrs = psutil.net_if_addrs()

    for name, addrs in if_addrs.items():
        # Check if the interface is up and not a loopback
        if name in if_stats and if_stats[name].isup and 'lo' not in name.lower() and 'loopback' not in name.lower():
            for addr in addrs:
                # We are interested in IPv4 addresses
                if addr.family == socket.AF_INET:
                    active_interfaces[name] = addr.address
                    break # Move to the next interface after finding the first IPv4

    return active_interfaces


def get_interface_name_by_ip(ip_address):
    """
    Finds the name of a network interface that has been assigned a specific IP address.

    Args:
        ip_address (str): The IPv4 address to search for.

    Returns:
        str or None: The name of the interface if found, otherwise None.
    """
    if_addrs = psutil.net_if_addrs()
    for name, addrs in if_addrs.items():
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address == ip_address:
                return name
    return None


if __name__ == '__main__':
    interfaces = get_active_interfaces()
    if interfaces:
        print("Found active interfaces:")
        for name, ip in interfaces.items():
            print(f"  - {name}: {ip}")
    else:
        print("No active non-loopback interfaces found.")
