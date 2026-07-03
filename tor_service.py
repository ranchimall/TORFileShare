"""Launches a self-contained Tor process with an ephemeral-on-disk hidden
service pointing at our local HTTP server. No system-wide torrc editing
required -- stem launches and owns its own Tor instance."""
import os
import stem.process


def start_tor_hidden_service(data_dir, socks_port, http_port):
    os.makedirs(data_dir, exist_ok=True)
    hs_dir = os.path.join(data_dir, "hidden_service")
    os.makedirs(hs_dir, exist_ok=True)
    os.chmod(hs_dir, 0o700)

    tor_data_dir = os.path.join(data_dir, "tor_data")
    os.makedirs(tor_data_dir, exist_ok=True)
    os.chmod(tor_data_dir, 0o700)

    def _log(line):
        if "Bootstrapped" in line:
            print(f"[tor] {line}")

    tor_process = stem.process.launch_tor_with_config(
        config={
            "SocksPort": str(socks_port),
            "HiddenServiceDir": hs_dir,
            "HiddenServicePort": f"80 127.0.0.1:{http_port}",
            "DataDirectory": tor_data_dir,
        },
        init_msg_handler=_log,
    )

    hostname_file = os.path.join(hs_dir, "hostname")
    with open(hostname_file, "r") as f:
        onion_address = f.read().strip()

    return tor_process, onion_address
