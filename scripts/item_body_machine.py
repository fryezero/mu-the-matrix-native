"""Reuse a Unicorn address space while restoring the declared fresh-world state.

Read-only text stays mapped. Data, explicitly mapped case regions and every BSS
page are restored before each call. Heap allocation/CRT epochs and case registries
restart too. Allocator services zero each allocation before use. The validator
compares this machine with separately constructed fresh machines before its sweep.
"""
import validate_renderchar as v
from renderchar_machine import DATA_BASE, HEAP, INIT_EPOCH, PAGE


class ResetWorld:
    def __init__(self, wa, factory=v.World):
        self.world = factory(*wa)
        m = self.world.m
        self.regions = [(address, m.read(address, size)) for address, size in m.mapped]
        self.regions.append((DATA_BASE, wa[1]))
        self.pages = {address: m.read(address, PAGE) for address in m.lazy}

    def __call__(self, *wa):
        w, m = self.world, self.world.m
        for address, payload in self.regions:
            m.write(address, payload)
        for address in m.lazy:
            m.write(address, self.pages.get(address, bytes(PAGE)))
        w.models.clear()
        w.records.clear()
        w.calls.clear()
        m.stopped = None
        m.heap = HEAP
        m.epoch = INIT_EPOCH
        return w
