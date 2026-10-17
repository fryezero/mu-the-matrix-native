#!/bin/zsh
# mu-step.sh <fx> <fy>: close helper dialog (if any), walk by clicking (fx,fy), then try enabling MU Helper; saves /tmp/step.png
: "${MU_BOTTLE:?select an existing test bottle}"
[[ "$MU_BOTTLE" != MuMatrix32 ]] || { print -u2 'MuMatrix32 is reserved'; exit 1; }
W='/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine'
$W --bottle "$MU_BOTTLE" 'C:\mutools\muinput.exe' wait "Name: [" 5 activate hold 120 click 0.501 0.569 sleep 300 click $1 $2 sleep 2600 mclick 0.5 0.45 sleep 700 >/dev/null 2>&1
cd "${0:A:h}" && swift winshot.swift "name: [" /tmp/stepfull.png >/dev/null 2>&1
sips -Z 700 /tmp/stepfull.png --out /tmp/step.png >/dev/null
