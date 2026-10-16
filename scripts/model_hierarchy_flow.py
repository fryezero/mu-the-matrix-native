#!/usr/bin/env python3
"""Slot dataflow of the client pose loop, without any matrix arithmetic.

This models only the control flow verified at 0x012b5064 (animated pose) and
0x012bcffb (action-0 pose) in the pinned restored text:

* bones are visited in index order 0..count-1;
* a record whose dummy byte is nonzero is skipped, so its output slot is not
  written by that call;
* parent == -1 composes with a global root matrix and writes slot i;
* any other parent value composes slot `parent` of the caller's output buffer
  with the local matrix and writes slot i.  No range, ordering or dummy check
  precedes that read.

The model reports where each slot's input came from.  It deliberately does not
choose a value for a slot the call never wrote: the client reads whatever the
caller's buffer already held there.
"""

WRITTEN = 'written-this-call'
UNWRITTEN = 'not-written-this-call'
OUTSIDE = 'outside-model-slots'


def pose_flow(bones):
    """Return one record per bone describing the verified slot dataflow.

    `bones` is a sequence of (dummy, parent) pairs.  `dummy` is the stored
    byte's truth value; `parent` is the signed 16-bit field.  Values for dummy
    records are ignored, as the client skips them before reading the parent.
    """
    count = len(bones)
    written = [False] * count
    depends_on_unwritten = [False] * count
    records = []
    for index, (dummy, parent) in enumerate(bones):
        if dummy:
            records.append({'bone': index, 'skipped': True})
            continue
        if not -0x8000 <= parent <= 0x7fff:
            raise ValueError('parent must be a signed 16-bit value')
        if parent == -1:
            source, inherited = 'root', False
        elif 0 <= parent < count:
            source = WRITTEN if written[parent] else UNWRITTEN
            inherited = source == UNWRITTEN or depends_on_unwritten[parent]
        else:
            source, inherited = OUTSIDE, True
        written[index] = True
        depends_on_unwritten[index] = inherited
        records.append({'bone': index, 'skipped': False, 'parent': parent,
                        'parent_slot': source, 'depends_on_slot_not_written_here': inherited})
    return records


def summarize(bones):
    records = pose_flow(bones)
    return {
        'bones': len(records),
        'skipped_dummy_records': sum(r['skipped'] for r in records),
        'direct_dummy_parent_reads': sum(
            1 for r in records if not r['skipped'] and 0 <= r['parent'] < len(bones)
            and bones[r['parent']][0]),
        'direct_unwritten_reads': sum(1 for r in records if r.get('parent_slot') == UNWRITTEN),
        'outside_reads': sum(1 for r in records if r.get('parent_slot') == OUTSIDE),
        'bones_depending_on_unwritten_slots': sum(
            1 for r in records if r.get('depends_on_slot_not_written_here')),
    }
