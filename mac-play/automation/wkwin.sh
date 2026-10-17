#!/bin/zsh
# wkwin.sh <seconds>: mean fps and mean work ms/frame from mugl stats written in the next N seconds
S="${MU_STATS_FILE:?select a private mugl statistics file}"
n0=$(wc -l < "$S" | tr -d ' '); sleep ${1:-20}
T=$(tail -n +$((n0 + 1)) "$S")
w=$(echo "$T" | grep -o "work=[0-9.]*" | cut -d= -f2 | awk '{s+=$1;n++} END {if (n) printf "%.2f", s/n}')
f=$(echo "$T" | grep -o " fps=[0-9.]*" | cut -d= -f2 | awk '{s+=$1;n++} END {if (n) printf "%.2f (n=%d)", s/n, n}')
echo "fps $f work ${w}ms"
