#!/bin/zsh
# Log in through an ALREADY RUNNING client's server list. No restart or installation.
# Required MU_BOTTLE, MU_GAME_DIR (host path), MU_ACCOUNT, MU_KEYCHAIN_SERVICE.
# The password is read from Keychain at runtime and is never printed or saved.
set -eu
: "${MU_BOTTLE:?select an existing test bottle}"
: "${MU_GAME_DIR:?host path to the cloned game directory}"
: "${MU_ACCOUNT:?account name}"
: "${MU_KEYCHAIN_SERVICE:?Keychain service name}"
if [[ "$MU_BOTTLE" == MuMatrix32 ]]; then
  print -u2 'MuMatrix32 is reserved; select an explicitly prepared test bottle'
  exit 1
fi
CX=/Applications/CrossOver.app/Contents/SharedSupport/CrossOver
W() { "$CX/bin/wine" --bottle "$MU_BOTTLE" "$@" 2>&1 | grep -v "Using a 32"; }
# If the launcher saved an Account ID (LauncherOption.if "ID:"), the game prefills it (focus stays in Account) -> just Tab.
LOPT="$MU_GAME_DIR/LauncherOption.if"
if grep -aFq "ID:$MU_ACCOUNT" "$LOPT" 2>/dev/null; then USERKEYS=(key 09); else USERKEYS=(type "$MU_ACCOUNT" key 09); fi
P=$(security find-generic-password -s "$MU_KEYCHAIN_SERVICE" -a "$MU_ACCOUNT" -w) || { echo "no keychain password"; exit 1; }
W 'C:\mutools\muinput.exe' wait "Powered by IGCN" 5 activate hold 250 click ${SUBSERVER_FX:-0.498} ${SUBSERVER_FY:-0.519} sleep 3000 "${USERKEYS[@]}" type "$P" key 0d sleep 6000 | grep -c click >/dev/null
unset P
W 'C:\mutools\muinput.exe' wait "Powered by IGCN" 5 activate key 0d sleep 10000 | grep -c fore >/dev/null
W 'C:\mutools\muinput.exe' wait "Name: [" 20 activate hold 250 click 0.499 0.769 sleep 1000 | grep -q click && echo "in world" || { echo "not in world"; exit 2; }
