#!/bin/zsh
# mu-coords.sh: crop the in-game HUD (map name + x,y) of the MU window into /tmp/coord.png
cd "${0:A:h}" && swift winshot.swift "name: [" /tmp/m.png >/dev/null 2>&1
python3 -c "
from PIL import Image; im=Image.open('/tmp/m.png'); w,h=im.size; im.crop((int(w*0.04),int(h*0.025),int(w*0.17),int(h*0.045))).resize((520,80)).save('/tmp/coord.png')"
