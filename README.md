# bw-sync — Bitwarden Dynamic Credential Provider for Royal TSX

A Python script that fetches credentials from your [Bitwarden](https://bitwarden.com) vault and exposes them to [Royal TSX](https://royalapps.com/ts/mac/features) as a **Dynamic Credential Provider**.

Credentials are read securely from **macOS Keychain** — no secrets are stored in the script or on disk.

---

## How it works

1. Royal TSX calls `bw-sync.py` when it needs credentials
2. The script reads your Bitwarden API key and master password from macOS Keychain
3. It logs in, unlocks, and syncs your Bitwarden vault via the Bitwarden CLI
4. It outputs all vault items as a JSON object in the Royal TSX credential format
5. Royal TSX maps those credentials to your connections automatically

---

## Prerequisites

- macOS
- [Python 3](https://www.python.org/downloads/)
- [Bitwarden CLI](https://bitwarden.com/help/cli/) installed via Homebrew:
  ```bash
  brew install bitwarden-cli
  ```
- A Bitwarden account with API key access (Personal API Key or Organization API Key)
- [Royal TSX](https://royalapps.com/ts/mac/features) for Mac

---

## Setup

### 1. Get your Bitwarden API credentials

1. Log in to the [Bitwarden Web Vault](https://vault.bitwarden.com)
2. Go to **Account Settings → Security → Keys → API Key**
3. Note your **Client ID** and **Client Secret**

### 2. Store credentials in macOS Keychain

Run the setup script — it will prompt for your credentials and store them securely in Keychain:

```bash
chmod +x setup-keychain.sh
./setup-keychain.sh
```

You can verify the entries in **Keychain Access.app** by searching for `bw-sync`.

### 3. Configure the script

Open `bw-sync.py` and edit the configuration section at the top:

```python
BW_PATH = "/opt/homebrew/bin/bw"   # Path to the Bitwarden CLI binary

ORGANIZATION_IDS = [
    "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  # Your Bitwarden Organization ID
]
```

To find your **Organization ID**:  
Bitwarden Web Vault → **Organizations** → your org → **Settings** → copy the Organization ID.

> Remove the `--organizationid` filter in `get_entries()` if you want all personal vault items instead.

### 4. Test the script

```bash
python3 bw-sync.py
```

Expected output:
- Log messages on **stderr** (login → unlock → sync → fetched N items)
- A JSON blob on **stdout** — this is what Royal TSX reads

### 5. Configure Royal TSX

1. Open Royal TSX and edit your document
2. Go to **Credentials** → add a **Dynamic Credential**
3. Set the **Script Interpreter** to `python3`
4. Set the **Script** path to the full path of `bw-sync.py`
5. Assign the dynamic credential to your connections

---

## Keychain entries reference

| Keychain Service | Keychain Account | Value                        |
|------------------|------------------|------------------------------|
| `BW_CLIENTID`    | `bw-sync`        | Your Bitwarden Client ID     |
| `BW_CLIENTSECRET`| `bw-sync`        | Your Bitwarden Client Secret |
| `BW_PASSWORD`    | `bw-sync`        | Your Bitwarden Master Password |

---

## Supported item types

| Bitwarden Type | Exported as          |
|----------------|----------------------|
| Login          | Credential (username, password, URL) |
| Card           | Credential with card fields as Custom Properties |
| Custom fields  | Custom Properties (Text, Protected, YesNo) |
| Notes          | Notes (HTML line breaks) |
| Multiple URIs  | Primary URL + extra URLs as Custom Properties |

---

## Security notes

- Credentials are stored in **macOS Keychain**, never in the script or environment variables
- The script logs to **stderr** only — the JSON credential output on stdout is kept clean
- The Bitwarden CLI session is closed (`bw logout`) after every run

---

## License

MIT
