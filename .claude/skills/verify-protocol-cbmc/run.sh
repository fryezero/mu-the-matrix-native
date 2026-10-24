#!/bin/sh
# Formal verification of native/core/mu_protocol.c with CBMC.
#
#   run.sh                 prove every property on the real source (exit 1 on any failure)
#   run.sh --only NAME     one harness (NAME from --list)
#   run.sh --trace NAME    one harness with CBMC's counterexample trace on stdout
#   run.sh --mutants       prove each property fails on the planted mistake that breaks it
#   run.sh --list          the harness table
#
# Needs cbmc and z3 on PATH:  brew install cbmc z3
# Environment: VERIFY_TIMEOUT (seconds per CBMC run, default 600), VERIFY_LOGDIR.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
HARNESS="$HERE/harness"
SRC="$ROOT/native/core/mu_protocol.c"
HDR="$ROOT/native/core/mu_protocol.h"
TIMEOUT="${VERIFY_TIMEOUT:-600}"
LOGDIR="${VERIFY_LOGDIR:-${TMPDIR:-/tmp}/verify-protocol-cbmc}"
mkdir -p "$LOGDIR"

CHECKS="--unwinding-assertions --bounds-check --pointer-check --pointer-overflow-check --signed-overflow-check --unsigned-overflow-check --conversion-check"
# xor_inverse: the descending loop's post-decrement wraps i to SIZE_MAX at exit
# when start is 0 (defined in C, value unused); the wrap check would flag it.
CHECKS_NO_UWRAP="--unwinding-assertions --bounds-check --pointer-check --pointer-overflow-check --signed-overflow-check --conversion-check"

# name | properties | backend | unwind | checks | mutant mode
# backend: sat = CBMC's built-in SAT solver; z3 = --smt2 (z3 on PATH).
#   z3 is needed where an index into the 0x2000-byte ring or the 0x145c-byte
#   packet object ranges over the whole object (recv_*, packet_add); CBMC's SAT
#   encoding does not finish there. SAT is needed where z3 proves the real code
#   but cannot build a counterexample for a planted mistake in reasonable time
#   (packet_build, packet_begin: the body offsets flow through memory).
# mutant mode: stop = --stop-on-fail (first counterexample); full = all
#   properties in one solve. Both are fast where listed; neither rescues the
#   other backend's slow cases.
TABLE='
frame_parse  P1    sat 4  full    full
recv_drain   R1,R2 z3  14 full    stop
recv_push    R3    z3  70 full    stop
packet_begin S1    sat 8  full    full
packet_build S1    sat 26 full    full
packet_add   S1    z3  26 full    stop
xor_inverse  S2    sat 26 nouwrap full
xor_window   S2    sat 24 full    full
xor_upper    S2    sat 24 full    full
'

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing $1: brew install cbmc z3" >&2; exit 2; }; }
need cbmc; need z3; need perl

# alarm_run SECONDS cmd...: run cmd under a time limit; exits 142 on timeout, else with cmd's status
alarm_run() {
    perl -e '
        my $t = shift; my $pid = fork; exit 2 unless defined $pid;
        if ($pid == 0) { exec @ARGV; exit 127 }
        local $SIG{ALRM} = sub { kill "KILL", $pid; waitpid $pid, 0; exit 142 };
        alarm $t; waitpid $pid, 0; alarm 0;
        exit(($? & 127) ? 128 + ($? & 127) : ($? >> 8) & 255);
    ' "$@"
}

row() { printf '%s\n' "$TABLE" | awk -v n="$1" '$1 == n'; }
names() { printf '%s\n' "$TABLE" | awk 'NF {print $1}'; }

# cbmc_run NAME SOURCE [extra cbmc args...]  -> prints result line, returns 0 pass / 1 fail / 2 error
cbmc_run() {
    name=$1; source=$2; shift 2
    set -- "$@"
    r=$(row "$name"); [ -n "$r" ] || { echo "unknown harness $name" >&2; return 2; }
    props=$(printf '%s' "$r" | awk '{print $2}')
    backend=$(printf '%s' "$r" | awk '{print $3}')
    unwind=$(printf '%s' "$r" | awk '{print $4}')
    checks=$(printf '%s' "$r" | awk '{print $5}')
    [ "$checks" = nouwrap ] && flags="$CHECKS_NO_UWRAP" || flags="$CHECKS"
    [ "$backend" = z3 ] && flags="$flags --smt2"
    log="$LOGDIR/$name${MUTANT_TAG:-}.log"
    start=$(date +%s)
    alarm_run "$TIMEOUT" cbmc "$HARNESS/$name.c" \
        -DMU_PROTOCOL_SOURCE="\"$source\"" --unwind "$unwind" $flags "$@" > "$log" 2>&1
    rc=$?
    secs=$(( $(date +%s) - start ))
    summary=$(grep -E '^\*\* [0-9]+ of [0-9]+ failed' "$log" | tail -1 | sed 's/^\*\* //')
    case $rc in
        0)  printf '[PASS]  %-13s %-6s %4ss  %s\n' "$name" "$props" "$secs" "$summary"; return 0 ;;
        10) printf '[FAIL]  %-13s %-6s %4ss  %s\n' "$name" "$props" "$secs" "$summary"
            # which property group failed: harness assertions carry the property label, CBMC's own checks are the memory-safety side
            grep -E ': FAILURE$' "$log" | sed 's/^/        /' | head -12
            grep -qE ': FAILURE$' "$log" || grep -A2 'Violated property' "$log" | grep -vE '^--$' | head -6 | sed 's/^/        /'
            if [ "$name" = recv_drain ]; then
                grep -qE '\[[a-z_]+\.assertion\.[0-9]+\].*FAILURE' "$log" && echo "        -> R2 (harness assertion) failed"
                grep -E 'FAILURE$' "$log" | grep -vqE '\.assertion\.' && echo "        -> R1 (CBMC memory-safety or unwinding check) failed"
            fi
            echo "        log: $log   trace: $0 --trace $name"
            return 1 ;;
        142) printf '[TIME]  %-13s %-6s %4ss  exceeded VERIFY_TIMEOUT=%s\n' "$name" "$props" "$secs" "$TIMEOUT"; return 2 ;;
        *)  printf '[ERROR] %-13s %-6s %4ss  cbmc exit %s, see %s\n' "$name" "$props" "$secs" "$rc" "$log"
            grep -iE 'error|invariant|reason' "$log" | head -5 | sed 's/^/        /'; return 2 ;;
    esac
}

# A planted mistake: NAME, sed program applied to a copy of the product source, harnesses that must fail.
MUTANTS='
parse-size-unchecked   |/if (size > avail)/{N;d;}                                                    |frame_parse recv_drain
parse-two-bytes        |s/if (avail < 3u)/if (avail < 2u)/                                           |frame_parse
drain-overlap          |s/off += info.size;/off += info.size - 1u;/                                   |recv_drain
push-no-guard          |/if (r->len + n > MU_RECV_CAP)/{N;d;}                                        |recv_push
add-no-guard           |/if ((uint64_t)cur + (uint64_t)len > (uint64_t)MU_PACKET_CAP) {/{N;N;N;d;}   |packet_add
add-size-off-by-one    |s/packet_set_size(p, cur + (uint32_t)len);/packet_set_size(p, cur + (uint32_t)len + 1u);/|packet_add packet_build
begin-keeps-overflow   |/^    p->overflow = 0u;$/d                                                    |packet_begin packet_build
begin-no-head          |s/mu_packet_add(p, \&head, 1u, 0);/\/* head add removed *\//                   |packet_begin
finish-wrong-byte      |s/p->obj\[3\] = (uint8_t)(size \& 0xffu);/p->obj[3] = (uint8_t)((size >> 8) \& 0xffu);/|packet_begin packet_build
encode-one-too-far     |s/for (i = start; i < end; ++i)/for (i = start; i <= end; ++i)/              |xor_upper xor_window
decode-ascending       |s/for (i = end; i-- > start;)/for (i = start; i < end; ++i)/                |xor_inverse
'

run_all() {
    echo "verify-protocol-cbmc: $(cbmc --version | head -1), z3 $(z3 --version | awk '{print $3}'), source $SRC"
    echo "logs in $LOGDIR"
    status=0
    for n in $(names); do cbmc_run "$n" "$SRC" || status=1; done
    [ $status -eq 0 ] && echo "RESULT: all properties hold on the real source (within the stated bounds)" \
                      || echo "RESULT: a property FAILED or did not finish; read the lines above"
    return $status
}

run_mutants() {
    echo "verify-protocol-cbmc --mutants: each planted mistake must make its property fail"
    status=0
    printf '%s\n' "$MUTANTS" | while IFS='|' read -r mname prog expect; do
        mname=$(printf '%s' "$mname" | tr -d ' '); [ -n "$mname" ] || continue
        prog=$(printf '%s' "$prog" | sed 's/[[:space:]]*$//')
        dir=$(mktemp -d "${TMPDIR:-/tmp}/mu-protocol-mutant.XXXXXX")
        cp "$HDR" "$dir/mu_protocol.h"
        sed -e "$prog" "$SRC" > "$dir/mu_protocol.c"
        if cmp -s "$SRC" "$dir/mu_protocol.c"; then
            echo "[STALE] $mname: the sed program matched nothing; the product changed, update MUTANTS"
            echo "$mname" >> "$LOGDIR/mutant-misses"; rm -rf "$dir"; continue
        fi
        echo "--- $mname: $(printf '%s' "$prog" | cut -c1-70)"
        for h in $expect; do
            # one counterexample is the point here; the table says whether --stop-on-fail is faster for this harness
            mode=$(row "$h" | awk '{print $6}'); extra=""; [ "$mode" = stop ] && extra="--stop-on-fail"
            MUTANT_TAG=".$mname" cbmc_run "$h" "$dir/mu_protocol.c" $extra > "$dir/out" 2>&1; rc=$?
            line=$(head -1 "$dir/out")
            case $rc in
                1) printf '[CAUGHT] %s\n' "$line" ;;
                0) printf '[MISSED] %s   <- the property did not notice this mistake\n' "$line"; echo "$mname/$h" >> "$LOGDIR/mutant-misses" ;;
                *) printf '[NOISE]  %s\n' "$line"; echo "$mname/$h" >> "$LOGDIR/mutant-misses" ;;
            esac
        done
        rm -rf "$dir"
    done
    if [ -s "$LOGDIR/mutant-misses" ]; then
        echo "RESULT: some planted mistakes were NOT caught: $(tr '\n' ' ' < "$LOGDIR/mutant-misses")"; rm -f "$LOGDIR/mutant-misses"; return 1
    fi
    echo "RESULT: every planted mistake was caught"; return 0
}

rm -f "$LOGDIR/mutant-misses"
case "${1:-}" in
    "")        run_all ;;
    --list)    printf '%s\n' "$TABLE" | awk 'NF' | awk 'BEGIN{print "name          props  backend unwind checks  mutant-mode"} {printf "%-13s %-6s %-7s %-6s %-7s %s\n",$1,$2,$3,$4,$5,$6}' ;;
    --only)    cbmc_run "$2" "$SRC" ;;
    --trace)   TIMEOUT="$TIMEOUT" cbmc_run "$2" "$SRC" --trace; grep -E ': FAILURE$' "$LOGDIR/$2.log"; echo; sed -n '/^Trace for/,$p' "$LOGDIR/$2.log" | head -400 ;;
    --mutants) run_mutants ;;
    *)         echo "usage: run.sh [--list | --only NAME | --trace NAME | --mutants]" >&2; exit 2 ;;
esac
