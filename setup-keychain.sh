#!/bin/bash
# Stores Bitwarden credentials in macOS Keychain for use with bw-sync.py.
# Run this once before using the script. Your credentials are never written to disk.

set -e

ACCOUNT="bw-sync"

echo "This will store your Bitwarden credentials in macOS Keychain."
echo "Account name used: '$ACCOUNT'"
echo ""

read -p  "Bitwarden Client ID     : " BW_CLIENTID
read -sp "Bitwarden Client Secret : " BW_CLIENTSECRET
echo
read -sp "Bitwarden Master Password: " BW_PASSWORD
echo
echo ""

security add-generic-password -U -a "$ACCOUNT" -s "BW_CLIENTID"     -w "$BW_CLIENTID"
security add-generic-password -U -a "$ACCOUNT" -s "BW_CLIENTSECRET" -w "$BW_CLIENTSECRET"
security add-generic-password -U -a "$ACCOUNT" -s "BW_PASSWORD"     -w "$BW_PASSWORD"

echo "Done. Credentials saved to Keychain under account '$ACCOUNT'."
echo "You can verify them in Keychain Access.app by searching for 'bw-sync'."
