# TORFileShare
A two-way file sync tool that connects peers over a private Tor hidden service (no central server), automatically pushing and reconciling changes across shared folders and subfolders. This project falls under the ProjectAI Token System of RanchiMall Artificial Intelligence Blockchain Contract AIBC.

# TorFileShare

A two-way, peer-to-peer file sync tool that connects peers over private Tor hidden services — **no central server, no port forwarding, no cloud storage**. Each peer runs its own ephemeral Tor hidden service; files dropped into a shared folder are automatically pushed to the peer in real time, and a periodic reconciliation catches anything missed (e.g. while a peer was offline).

> This project falls under the ProjectAI Token System of RanchiMall Artificial Intelligence Blockchain Contract AIBC.

---

## How it works

- **`tor_service.py`** — Launches a self-contained Tor process (via `stem`) with its own ephemeral hidden service. No system-wide `torrc` editing required.
- **`server.py`** — A lightweight HTTP server bound only to `127.0.0.1`, reachable *only* through your Tor hidden service. Exposes `/list`, `GET /file/<path>`, and `POST /file/<path>`.
- **`client.py`** — Talks to a peer's hidden service over Tor's SOCKS5 proxy.
- **`utils.py`** — Shared helpers: file hashing/listing and safe path resolution (prevents path traversal).
- **`sync.py`** — Watches your shared folder for changes and pushes them immediately, plus runs a periodic two-way reconciliation.
- **`main.py`** — Entry point that wires everything together.

Your `.onion` address isn't a secret key, but anyone who has it can read/write your shared folder — so exchange it only over a trusted channel (Signal, in person, etc.), not publicly.

---

## Requirements

- Python 3.8+
- The Tor binary (`tor` / `tor.exe`) installed and available on your system `PATH`
- Python packages listed in `requirements.txt`:
  - `requests`
  - `PySocks`
  - `stem`
  - `watchdog`

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/TorFileShare.git
cd TorFileShare
```

### 2. Install Tor

#### Windows
1. Download the **Tor Expert Bundle** from the [official Tor Project downloads page](https://www.torproject.org/download/tor/).
2. Extract it somewhere permanent, e.g. `C:\Tor\`.
3. Add that folder (the one containing `tor.exe`) to your **PATH**:
   - Search "Environment Variables" in the Start menu → *Edit the system environment variables* → *Environment Variables*
   - Under **User variables**, select `Path` → **Edit** → **New** → paste the folder path (e.g. `C:\Tor\`)
   - Click OK on all dialogs, then open a **new** terminal window
4. Verify it works:
   ```powershell
   tor --version
   ```

#### Linux (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install tor
```

#### Linux (Fedora)
```bash
sudo dnf install tor
```

#### Linux (Arch)
```bash
sudo pacman -S tor
```

Verify:
```bash
tor --version
```

> **Note:** You don't need to *start* the system Tor service (`systemctl start tor`) — this project launches and manages its own private Tor instance automatically. Just having the `tor` binary installed is enough.

### 3. Set up a Python virtual environment (recommended)

#### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Running TorFileShare

Run the exact same script on both machines you want to sync between.

### Step 1 — Start on Peer A

#### Windows
```powershell
python main.py --shared-dir .\shared
```

#### Linux
```bash
python3 main.py --shared-dir ./shared
```

You'll see output like:

```
[tor] starting Tor and creating hidden service (can take 10-60s the first time)...
[tor] your onion address: abcdefgh1234ijklmnopqrstuvwx5678yzabcdefgh1234ijklmnop.onion
[tor] share this with your peer over a secure channel.
[server] serving ./shared on 127.0.0.1:8000 (reachable via Tor only)
[sync] no peer set yet. Once you have their onion address, write it into:
       ./tor_data/peer.txt
       (or restart this script with --peer <onion_address>)
```

### Step 2 — Start on Peer B

Run the same command on the second machine (in its own copy of the project):

```bash
python3 main.py --shared-dir ./shared
```

It will also print its own `.onion` address.

### Step 3 — Exchange onion addresses

Send each `.onion` address to the other person over a trusted channel — Signal, iMessage, in person, etc.

### Step 4 — Set the peer

The peer's onion address is stored in a single file:

```
tor_data/peer.txt
```

**You don't need to create this file (or the `tor_data` folder) yourself ahead of time** — `main.py` creates the `tor_data` folder automatically the first time you run it. You only need to create or edit `peer.txt` once you actually have the other person's onion address in hand.

The file should contain **only the peer's onion address** — not your own — with no extra text, quotes, or blank lines. For example:

```
abcdefgh1234ijklmnopqrstuvwx5678yzabcdefgh1234ijklmnop.onion
```

There are two ways to set it:

**Option A — pass it at startup with `--peer`** (this writes `peer.txt` for you):
```bash
python3 main.py --shared-dir ./shared --peer <their_onion_address>
```

**Option B — write it directly into `tor_data/peer.txt`** while the script is already running. This is the "add it into peer.txt" step — no restart is needed, the file is watched and re-read automatically:

**Linux:**
```bash
echo "<their_onion_address>" > ./tor_data/peer.txt
```

**Windows (PowerShell):**
```powershell
"<their_onion_address>" | Out-File -Encoding ascii .\tor_data\peer.txt
```

**Windows (Notepad, if you prefer a GUI):**
1. Navigate to the `tor_data` folder inside your project directory (it appears after the first run).
2. Create a new text file named `peer.txt` (make sure Notepad doesn't append `.txt.txt` — enable "Show file extensions" in File Explorer to check).
3. Paste in the peer's onion address, save, and close.

Either way, once `peer.txt` contains a valid onion address, the console will start printing reconciliation activity with that peer.

### Step 5 — Sync files

Once both sides have set each other's peer address:

- Drop a file into `shared/` on either machine → it's pushed to the peer within seconds
- Every `--sync-interval` seconds (default `60`), a full two-way reconciliation runs automatically, catching anything missed while a peer was offline

To stop, press `Ctrl+C` on either machine — this shuts down the local Tor process cleanly.

---

## Command-line options

| Flag | Default | Description |
|---|---|---|
| `--shared-dir` | `./shared` | Folder to sync |
| `--data-dir` | `./tor_data` | Folder for Tor state, hidden service keys, and `peer.txt` |
| `--http-port` | `8000` | Local HTTP server port |
| `--socks-port` | `9050` | Local Tor SOCKS proxy port |
| `--peer` | *(none)* | Peer's `.onion` address |
| `--sync-interval` | `60` | Seconds between full two-way reconciliations |

---

## Running multiple instances on the same machine (for testing)

Give each instance its own data directory and ports so they don't collide:

```bash
python3 main.py --shared-dir ./shared_a --data-dir ./tor_data_a --http-port 8001 --socks-port 9051
python3 main.py --shared-dir ./shared_b --data-dir ./tor_data_b --http-port 8002 --socks-port 9052
```

---

## Security notes

- The local HTTP server binds only to `127.0.0.1` — it is never exposed directly to your LAN or the public internet, only reachable through your Tor hidden service.
- All file paths from peers are validated with `safe_join()` to prevent path traversal (e.g. `../../etc/passwd`).
- Your `.onion` address grants read/write access to your shared folder to whoever holds it — treat it like a shared secret, not a public link.

---

- No conflict resolution: if both peers edit the same file at the same time, the outcome depends on sync timing/order — last reconciliation wins.
- No deletion propagation.
- Designed for a two-peer relationship; multi-peer topologies would require extending `peer.txt` to support a list of peers.

---


