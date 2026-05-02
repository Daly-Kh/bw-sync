from __future__ import print_function

import sys
import json
import subprocess
import os
import logging

# Logging goes to stderr so it never pollutes the JSON stdout that Royal TSX reads
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
BW_PATH = "/opt/homebrew/bin/bw"
KEYCHAIN_ACCOUNT = "bw-sync"
ORGANIZATION_IDS = [
    # Add your Bitwarden organization ID(s) here.
    # Find it in the Bitwarden Web Vault: Settings → Organizations → <your org> → Settings → Organization ID
    # "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
]
# ─────────────────────────────────────────────────────────────────────────────


def get_keychain_secret(service):
    """Read a secret from macOS Keychain by service name."""
    result = subprocess.run(
        ["security", "find-generic-password", "-a", KEYCHAIN_ACCOUNT, "-s", service, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error("Failed to retrieve '%s' from Keychain. Run setup-keychain.sh first.", service)
        sys.exit(1)
    return result.stdout.strip()


def logout(path):
    subprocess.run([path, "logout"], capture_output=True)


def bitwarden_login(path, user_id, user_secret):
    logout(path)
    result = subprocess.run(
        [path, "login", "--apikey"],
        env={"BW_CLIENTID": user_id, "BW_CLIENTSECRET": user_secret, **os.environ},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error("Login failed: %s", result.stderr.strip())
        sys.exit(1)
    log.info("Logged in to Bitwarden successfully.")


def bitwarden_unlock(path, user_password):
    result = subprocess.run(
        [path, "unlock", "--passwordenv", "BW_PASSWORD"],
        env={"BW_PASSWORD": user_password, **os.environ},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error("Unlock failed: %s", result.stderr.strip())
        sys.exit(1)

    # The session key is the last token on the last line of the unlock output
    session_key = result.stdout.split()[-1].strip()
    if not session_key:
        log.error("Could not parse session key from unlock output.")
        sys.exit(1)

    log.info("Vault unlocked successfully.")
    return session_key


def bitwarden_sync(path, session_key):
    result = subprocess.run(
        [path, "sync", "--session", session_key],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error("Sync failed: %s", result.stderr.strip())
        sys.exit(1)
    log.info("Vault synced successfully.")


def convert_notes_to_html(notes):
    if not notes:
        return ""
    return notes.replace("\r\n", "<br />").replace("\r", "<br />").replace("\n", "<br />")


def create_credential(item):
    item_id = item["id"]
    item_type = item["type"]
    item_name = item["name"]
    item_notes = convert_notes_to_html(item.get("notes"))
    item_favorite = item.get("favorite", False)

    item_username = ""
    item_password = ""
    item_urls = []
    item_custom_properties = []

    item_login = item.get("login")
    if item_login:
        item_username = item_login.get("username") or ""
        item_password = item_login.get("password") or ""
        # Collect all URIs instead of overwriting — keep first as primary URL
        item_urls = [u.get("uri", "") for u in (item_login.get("uris") or []) if u.get("uri")]

    if item_type == 3:  # Card
        item_card = item.get("card")
        if item_card:
            card_brand = item_card.get("brand", "Credit Card")
            item_custom_properties.append({"Type": "Header", "Name": card_brand})

            for field_key, prop_name, prop_type in [
                ("cardholderName", "Cardholder", "Text"),
                ("number", "Card Number", "Text"),
                ("expMonth", "Expiration Month", "Text"),
                ("expYear", "Expiration Year", "Text"),
            ]:
                value = item_card.get(field_key)
                if value is not None:
                    item_custom_properties.append({"Type": prop_type, "Name": prop_name, "Value": value})

            code = item_card.get("code")
            if code is not None:
                item_custom_properties.append({"Type": "Protected", "Name": "Security Code", "Value": code})

    for item_field in item.get("fields") or []:
        field_type = item_field["type"]
        field_name = item_field.get("name") or ""
        field_value = item_field.get("value") or ""

        if field_type == 1:
            prop_type = "Protected"
        elif field_type == 2:
            prop_type = "YesNo"
            field_value = bool(field_value)
        else:
            prop_type = "Text"

        item_custom_properties.append({"Type": prop_type, "Name": field_name, "Value": field_value})

    # Extra URLs (beyond the first) stored as custom properties
    for i, url in enumerate(item_urls[1:], start=2):
        item_custom_properties.append({"Type": "Text", "Name": f"URL {i}", "Value": url})

    return {
        "Type": "Credential",
        "ID": item_id,
        "Name": item_name,
        "Notes": item_notes,
        "Favorite": item_favorite,
        "Username": item_username,
        "Password": item_password,
        "URL": item_urls[0] if item_urls else "",
        "CustomProperties": item_custom_properties,
    }


def get_entries():
    client_id = get_keychain_secret("BW_CLIENTID")
    client_secret = get_keychain_secret("BW_CLIENTSECRET")
    password = get_keychain_secret("BW_PASSWORD")

    bitwarden_login(BW_PATH, client_id, client_secret)
    session_key = bitwarden_unlock(BW_PATH, password)
    bitwarden_sync(BW_PATH, session_key)

    store_objects = []

    for org_id in ORGANIZATION_IDS:
        log.info("Fetching items for org: %s", org_id)
        result = subprocess.run(
            [BW_PATH, "list", "items", "--organizationid", org_id, "--session", session_key],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.error("Failed to list items for org %s: %s", org_id, result.stderr.strip())
            sys.exit(1)

        try:
            items = json.loads(result.stdout.strip())
        except json.JSONDecodeError as e:
            log.error("Failed to parse JSON for org %s: %s", org_id, e)
            sys.exit(1)

        for item in items:
            store_objects.append(create_credential(item))

        log.info("Fetched %d items for org %s.", len(items), org_id)

    logout(BW_PATH)
    print(json.dumps({"Objects": store_objects}))


get_entries()
