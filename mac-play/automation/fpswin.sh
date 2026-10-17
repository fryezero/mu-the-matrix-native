#!/bin/zsh
# fpswin.sh <seconds>: print mugl fps samples written during the next N seconds and their mean
S="${MU_STATS_FILE:?select a private mugl statistics file}"
n0=$(wc -l < "$S" | tr -d ' '); sleep ${1:-30}
tail -n +$((n0 + 1)) "$S" | grep -o "fps=[0-9.]*" | cut -d= -f2 | awk '{s+=$1; n++; printf "%s ", $1} END {if (n) printf "| mean %.2f (n=%d)\n", s/n, n}'
