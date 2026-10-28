#!/usr/bin/env python3
"""Read-only attribution of Aida's saved light grid, no live client access.

For type 30, green minus red per AddTerrainLight call is exactly 0.2 times
its range-2 falloff, independently of the random flicker. Dividing a saved
cell's primary-subtracted channel difference by that value estimates how
many uncleared additions contributed. Overlapping sources and binary32
accumulation limit the inference. Output stays in a caller-selected local file.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import fidelity_tour as ft

def analyze(objects, lights, tile):
    world, _, records = ft.read_objects(objects)
    if world not in (33,54):
        raise ValueError('expected an Aida object snapshot')
    light = ft.read_light(lights)
    if light['primary'] is None or light['frame'] is None:
        raise ValueError('expected both primary and frame light grids')
    out = []
    for _,_,o in records:
        if struct.unpack_from('<i',o,0x5c)[0] != 30: continue
        x,y,_ = struct.unpack_from('<3f',o,0x158)
        x,y = x/100.0,y/100.0
        if math.hypot(x-tile[0],y-tile[1]) > 3: continue
        samples = []
        for yy in range(int(y)-2,int(y)+3):
            for xx in range(int(x)-2,int(x)+3):
                falloff = (2-math.hypot(x-xx,y-yy))/2
                if falloff < 0.1: continue
                i = 3*((yy&255)*256+(xx&255))
                delta = [light['frame'][i+k]-light['primary'][i+k] for k in range(3)]
                samples.append({'tile':[xx,yy], 'effective_updates':round((delta[1]-delta[0])/(0.2*falloff),4),
                                'red_minus_blue':round(delta[0]-delta[2],4)})
        out.append({'type':30, 'tile':[x,y], 'samples':samples})
    return {'inputs': {name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                       for name, path in [('objects', objects), ('light', lights)]},
            'world': world, 'method':'type-30 channel difference divided by its range-2 falloff',
            'boundary':'inference; reset box and time history are absent from the snapshots','sources':out}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--objects',type=Path,required=True);p.add_argument('--light',type=Path,required=True)
    p.add_argument('--tile',type=int,nargs=2,default=[96,7]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.write_text(json.dumps(analyze(a.objects,a.light,a.tile),indent=2)+'\n')
if __name__=='__main__':main()
