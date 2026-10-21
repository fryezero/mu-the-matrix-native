"""Portable checks of reconstructed/price (NATIVE-LANG-002).

The client comparison is scripts/validate_item_price.py (Unicorn, private
captures and the installed Item.bmd).  These checks build libitemprice and
compare it with an independent Python statement of ItemValue 0x0169320b and
ConvertRepairGold 0x016b8d16 over synthetic records and random item states,
plus worked examples, the goldType rules and the zen formatting.
"""
import ctypes
import math
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
LIB = HERE/('libitemprice.dylib' if sys.platform == 'darwin' else 'libitemprice.so')


class Item(ctypes.Structure):
    _fields_ = [('code', ctypes.c_int32), ('level', ctypes.c_int32), ('durability', ctypes.c_uint8),
                ('max_durability', ctypes.c_uint8), ('set_bits', ctypes.c_uint8), ('special_count', ctypes.c_uint8),
                ('special', ctypes.c_uint16*8), ('special_value', ctypes.c_uint16*8), ('skill', ctypes.c_uint16),
                ('flag_72', ctypes.c_uint8), ('slot_73', ctypes.c_uint8*5), ('socket_count', ctypes.c_uint8),
                ('socket', ctypes.c_uint8*5), ('socket_level', ctypes.c_uint8*5), ('period', ctypes.c_uint8),
                ('expired', ctypes.c_uint8), ('excellent', ctypes.c_uint8), ('excellent_options', ctypes.c_uint8*9),
                ('harmony', ctypes.c_int32)]


RECORD_OF = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32)
SOUL_OF = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int32)


class State(ctypes.Structure):
    _fields_ = [('world', ctypes.c_int32), ('sell_flag', ctypes.c_uint8),
                ('socket_seed', ctypes.POINTER(ctypes.c_int32)), ('record_of', RECORD_OF),
                ('soul_conversion', SOUL_OF), ('user', ctypes.c_void_p), ('pet_status', ctypes.c_int32),
                ('pet_value', ctypes.c_uint32)]


class Repair(ctypes.Structure):
    _fields_ = [('shop_visible', ctypes.c_int), ('shop_repair_flag', ctypes.c_int),
                ('inventory_visible', ctypes.c_int), ('discount_percent', ctypes.c_int32)]


# ---- independent statement -------------------------------------------------

def i32(v):
    return (v + (1 << 31)) % (1 << 32) - (1 << 31)


def i64(v):
    return (v + (1 << 63)) % (1 << 64) - (1 << 63)


def tdiv(a, b):
    q = abs(a)//abs(b)
    return q if (a >= 0) == (b > 0) else -q


def f32(x):
    try:
        return struct.unpack('<f', struct.pack('<f', x))[0]
    except OverflowError:
        return math.copysign(math.inf, x)


def dtol(x):
    if math.isnan(x) or x >= 2.0**63 or x < -2.0**63:
        return -(1 << 63)
    return math.trunc(x)


def frac(g, num, den):
    return i64(g + dtol(float(g)*num/den))


def rounded(g):
    if g >= 1000:
        return tdiv(g, 100)*100
    if g >= 100:
        return tdiv(g, 10)*10
    return g


class Model:
    """ItemValue and ConvertRepairGold restated from the instruction listing."""

    def __init__(self, records=None, seeds=None, soul=()):
        self.records, self.seeds, self.soul = records or {}, seeds or [0]*256, set(soul)

    def value(self, r, it, gt, world=0, flag=0, pet=(-1, 0), depth=0):
        code, n, L = it['code'], it['durability'], it['level'] & 15
        if code == -1:
            return 0
        if gt == 1 and flag:
            return 1
        ok = 0 <= code <= 0x2c00
        ka = lambda k: ok and r[0x250] == k
        kb = lambda k: ok and r[0x251] == k
        ty = lambda k: ok and r[0x252] == k
        exc = ok and it['excellent'] == 1
        st = ok and it['set_bits'] & 0x33 != 0
        grp = any(ka(k) for k in (0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x38))
        exc_opts = [o for o in it['excellent_options'] if o != 0xff]
        stack = r[0x2af]
        zen = struct.unpack_from('<i', r, 0x28c)[0]
        if zen:
            g = zen if gt == 0 else tdiv(zen, 3)
            g = rounded(g)
            if stack:
                g = i64(g*n)
            return i32(g)
        lvl = r[0x254] | r[0x255] << 8
        lvl += 3*L
        if exc_opts and not ka(6) and not grp:
            lvl += 25
        elif grp:
            lvl += 25 if exc else 35 if st else 0
        w3 = world == 0x5c and gt == 0
        g = self.chain(r, it, code, n, L, w3)
        if g is None:
            out = self.general(r, it, code, n, L, lvl, gt, world, ka, kb, ty, exc, st, grp, exc_opts, depth, pet, flag)
            if out[0] == 'return':
                return out[1]
            g = out[1]
        g = min(g, 3000000000)
        if gt == 2:
            g = rounded(g)
        if gt:
            g = tdiv(g, 3)
        g = self.post(r, it, code, n, gt, g, ka, kb, ty, grp, pet)
        if g is None:
            return -1
        return i32(rounded(g))

    @staticmethod
    def chain(r, it, code, n, L, w3):
        x3 = lambda v: v*3 if w3 else v
        if code in (0x807, 0x80f):
            k = ([100, 1400, 2200, 3000] if code == 0x807 else [70, 1200, 2000, 2800])[L] if L < 4 else 0
            return x3(tdiv(i32(n*k), r[0x268]) if r[0x268] else 0)
        table = {0x1c0d: i32(n*3000000), 0x1c0e: n*1800000, 0x180f: n*810000, 0x1c10: i32(n*15000000),
                 0x1c16: i32(n*12000000), 0x1c8d: 672000, 0x1c8e: 546000, 0x1c8f: 471000, 0x1c90: 363000,
                 0x1cce: 5000, 0x1ccf: 0, 0x1cd0: 0, 0x1a0f: 9000000, 0x1c1c: 210000, 0x1c1d: n*30000,
                 0x1c6e: n*30000, 0x1c6f: x3(600000), 0x1c66: x3(30000), 0x1c6d: x3(30000), 0x286c: x3(n*30000),
                 0x1a1d: x3(5000), 0x1c14: 900, 0x1c33: 200000, 0x1c3f: 200000, 0x1c34: 99, 0x1c0a: x3(750),
                 0x1c1f: i32(n*21000000), 0x1c23: 2000*n, 0x1c24: 4000*n, 0x1c25: 6000*n, 0x1c26: 2500*n,
                 0x1c27: 5000*n, 0x1c28: 7500*n, 0x1c55: 300*n, 0x1c56: 300*n, 0x1c57: 300*n, 0x1a91: n*30000,
                 0x1a92: 600000, 0x1a93: n*300000, 0x1890: n*300000, 0x1892: n*300000, 0x1896: n*3000000,
                 0x1897: i32(n*9000000), 0x1920: n*80000000, 0x1d22: n*3000, 0x1d3c: 6000000,
                 0x1d40: n*3000000, 0x1d3d: 60000000, 0x1dd4: n*300000}
        table.update({c: 1500000 for c in range(0x1d35, 0x1d39)})
        table.update({c: 9000 for c in (0x1c17, 0x1c18, 0x1c19, 0x1c1a, 0x1c41, 0x1c42, 0x1c43, 0x1c44)})
        table.update({c: n*30000 for c in (0x1c65, 0x1c67, 0x1c68, 0x1c69, 0x1c6a, 0x1c6b, 0x1c6c)})
        if code in table:
            return table[code]
        if code == 0x1a0e:
            return {0: 180000, 1: 2400000}.get(L, 0)
        if code == 0x1a03:
            k = it['special_count']
            return 960000 + 300000*sum(1 for s in it['special'][:k] if s in (9, 10, 11))
        if code in (0x1a10, 0x1a11):
            return [15000, 10000, 50000, 100000, 300000, 500000, 800000, 1000000, 1200000][L] if L <= 8 else 0
        if code == 0x1a12:
            return 3*(50000 if L == 1 else (L-1)*20000+200000)
        if code == 0x1c15:
            return 9000 if L <= 2 else n*3900 if L == 3 else 0
        if code in (0x1c11, 0x1c12, 0x1c13):
            t = [[30000, 10000, 50000, 100000, 300000, 500000, 800000, 1000000],
                 [30000, 15000, 75000, 150000, 450000, 750000, 1200000, 1500000],
                 [120000, 60000, 84000, 120000, 180000, 240000, 300000, 180000]][code-0x1c11]
            return t[min(L, 7)]
        if code in (0x1a31, 0x1a32, 0x1a33):
            return {1: 500000, 2: 600000, 3: 800000, 4: 1000000, 5: 1200000, 6: 1400000}.get(L, 9000)
        if code == 0x1c09 and L == 1:
            return 1000
        if code == 0x1c07:
            return {0: n*900000, 1: n*450000}.get(L, 0)
        if code == 0x1a07:
            return x3({0: 1500000, 1: 1200000}.get(L, 0))
        if code == 0x1a0b:
            return {0: 100000, 1: 2400000}.get(L, 0)
        return None

    def general(self, r, it, code, n, L, lvl, gt, world, ka, kb, ty, exc, st, grp, exc_opts, depth, pet, flag):
        stack = r[0x2af]
        if r[0x288]:
            g = tdiv(r[0x288]**2*10, 12)
            if ka(9) and stack:
                g *= n
            if code in (0x1c03, 0x1c06):
                g = 1500
            if 0x1c00 <= code <= 0x1c08:
                if world == 0x5c and gt == 0:
                    g *= 3
                if L > 0:
                    g *= 2**L
                g = tdiv(g, 10)*10*n
                if gt:
                    g = tdiv(tdiv(g, 3), 10)*10
                return 'return', i32(g)
            return 'tail', g
        if code == 0x1a14:
            return 'tail', 3000 if L == 0 else 0
        if code in (0x1a34, 0x1a35):
            return 'tail', 3000000
        if code == 0x1a1f:
            return 'tail', {0: 9000000, 1: 4500000}.get(L, 0)
        base = r[0x254] | r[0x255] << 8
        if ka(0x19):
            e = i32(base*(L+50)*(L*10)*L + 100000)
            return 'tail', dtol(float(e)*(it['socket_count']*0.8))
        if ka(0x1a) or kb(0x2c):
            x = base + 5*sum(b >> 4 for b in it['slot_73'] if b != 0xff)
            return 'tail', i32(it['socket_count']*2*i32((x+40)*x*tdiv(x, 8)+100))
        if kb(0x64) or ka(0xb):
            return 'tail', 0
        typ = tdiv(code, 512)
        k = it['special_count']
        if typ in (0xc, 0xd, 0xf) and not ka(6):
            g = i32(lvl**3+100)
            for s, v in zip(it['special'][:k], it['special_value'][:k]):
                if s == 6:
                    g = g*v + g
                elif s == 0:
                    g = tdiv(g*v, 4) + g
            return 'tail', g
        if 5 <= L <= 15:
            lvl += [4, 10, 25, 45, 65, 95, 135, 185, 245, 305, 365][L-5]
        if ka(6) and not kb(0x16):
            g = i32((lvl+40)*lvl*lvl*11) + 40000000
        else:
            g = i32(tdiv(i32((lvl+40)*lvl*lvl), 8) + 100)
        if 0 <= typ <= 6 and r[0x253] == 0:
            g = tdiv(g*80, 100)
        if it['skill'] in (0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x38, 0x104, 0x105, 0x10e):
            g += dtol(f32(f32(float(g))*1.5)) & 0xffffffff
        ladder = lambda g, v, step: frac(g, {1: 6.0, 2: 14.0, 3: 28.0, 4: 56.0}[v//step], 10.0) \
            if v % step == 0 and 1 <= v//step <= 4 else g
        for s, v in zip(it['special'][:k], it['special_value'][:k]):
            if s in (0, 1, 2, 4, 6):
                if ka(6):
                    g = ladder(g, v*4 if s == 6 else v, 4)
                elif grp and st:
                    pass
                elif ty(2) and ka(2):
                    if v in (1, 2, 3):
                        g = frac(g, [6.0, 14.0, 28.0][v-1], 10.0)
                else:
                    g = ladder(g, v, 4)
            elif s == 3:
                g = ladder(g, v, 5)
            elif s in (5, 10, 11):
                g = frac(g, 25.0, 100.0)
            elif s in (7, 8, 9, 12):
                g = g*2
        if exc_opts and not grp:
            for _ in exc_opts:
                g += dtol(float(g)*25.0/100.0) if ka(6) else g
        elif grp:
            if exc:
                g = dtol(float(g)*2.0**len(exc_opts))
            elif st and not ka(0x2e):
                b = it['slot_73'][3]
                g = dtol(float(g)*2.0**(1 + ((b & 0x38) >> 3 != 7) + (b & 7 != 7)))
        if it['flag_72'] == 1:
            g = frac(g, 16.0, 100.0)
        if ty(2):
            add = tdiv(g*it['socket_count']*7, 10)
            for i in range(it['socket_count']):
                sid = it['socket'][i]
                if sid == 0xff:
                    continue
                lv = it['socket_level'][i]
                c2 = (lv-1-(5 if lv > 5 else 0))*6 + (0x1937 if lv > 5 else 0x1864) + self.seeds[sid]-1
                if c2 in self.records:
                    sphere = blank()
                    sphere['code'] = c2
                    add += self.value(self.records[c2], sphere, 0, world, flag, pet, depth+1)
            g += add
        g += i32(it['harmony']*50000)
        if stack:
            g *= n
        return 'tail', g

    def post(self, r, it, code, n, gt, g, ka, kb, ty, grp, pet):
        g = {0x1a20: n*50, 0x1a21: n*100, 0x1a22: n*1000, 0x1a23: n*10000, 0x1a24: 30000, 0x1a25: 50000}.get(code, g)
        if 0x1c2d <= code <= 0x1c32 or 0x1db0 <= code <= 0x1db7 or code in (0x1ce0, 0x1d07, 0x1d08):
            g = n*100
        if 0x1c99 <= code <= 0x1c9c:
            g = n*1000
        elif 0x1c9d <= code <= 0x1c9f:
            g = 10000
        if code in (0x18de, 0x18e8, 0x18f2, 0x18fc, 0x1904):
            g = 1
        if code == 0x18db:
            g = 0
        if 0x1a47 <= code <= 0x1a4b:
            g = 1000000
        if code in (0x1a04, 0x1a05, 0x28f7, 0x28f8, 0x28f9, 0x28fa, 0x2900):
            if pet[0] == -1:
                return None
            g = pet[1]
        if code in (0x1a70, 0x1a40, 0x1a41, 0x1a4c, 0x1a4d, 0x1a4e, 0x1a50, 0x1a6d, 0x1a6e, 0x1a6f, 0x1a71, 0x1a72,
                    0x1a73, 0x1aa6, 0x1c70, 0x1c71, 0x1c79, 0x1c7a, 0x1c7b, 0x1c7c, 0x298d, 0x298e):
            g = 1000
        elif code in (0x1a7a, 0x1a7b, 0x1aa3, 0x1aa4, 0x1aa5):
            g = 2000
        elif code in (0x1882, 0x1883, 0x1884, 0x1885, 0x1886, 0x1887, 0x189a, 0x18ac, 0x1916):
            g = 80
        if ty(5) and gt == 1:
            g = 0
        if (any(ka(k) for k in (0xe, 0xf, 0x12, 0x1b, 0x21, 0x37)) or grp) and it['period'] == 1 and \
                it['expired'] == 1 and gt == 1:
            g = 0
        if ty(2) and ka(2):
            g = tdiv(g, 100)
        if ty(4):
            g = 0
        fixed = {0x1b0c: 1000000000, 0x190a: 100000000, 0x190b: 1000000, 0x19e0: 1000000, 0x1aa9: 30000,
                 0x1aaa: 30000, 0x1cea: 1000000, 0x1d86: n*1000, 0x18d7: 1}
        fixed.update({c: 100000 for c in range(0x1cd9, 0x1cde)})
        fixed.update({c: 1000000 for c in range(0x1cf5, 0x1cf8)})
        fixed.update({c: 1000 for c in list(range(0x1d0d, 0x1d15)) + [0x1d17, 0x1d18]})
        g = fixed.get(code, g)
        if ka(0xc):
            g = 200000 if kb(0) else (900000 if gt == 0 else 300000) if code == 0x20ef else \
                1000000 if code == 0x20f0 else 0
        if 0x1d1a <= code <= 0x1d1c:
            g = 1000000
        if code == 0x29:
            g = 100000
        if code == 0x1bfe:
            g = n*100000
        if r[0x2b0] or r[0x2b1]:
            g = 0
        if gt == 1 and code in (0x1b98, 0x1da4, 0x1d73, 0x1d74, 0x1d75, 0x1c45):
            g = 0
        if gt == 1 and code == 0x1920:
            g = n*1000
        if gt == 1 and code == 0x1d59:
            g = 5000
        if code in (0x1dae, 0x1d93, 0x1d94, 0x1d95):
            g = n*1000
        if code in (0x1dbe, 0x1dc3):
            g = 0
        if code in self.soul:
            g = 10000
        g = {0x1dd2: n*100000, 0x1dd3: n*200000, 0x1dd4: n*500000, 0x1dd5: n*30000, 0x1dd6: n*900000,
             0x1dd7: n*50000, 0x1ddd: n*500000, 0x2915: n*1000, 0x2934: n*1000}.get(code, g)
        if 0x1dd8 <= code <= 0x1ddc:
            g = 1000000
        if ka(0x39) or ka(0x3a) or ka(0x17):
            g = i32(n*10000000)
        if ka(0x18):
            g = n*1000000
        if ka(0x1c):
            g = 200000
        if kb(0x5c):
            g = n*50000
        g = {0x285e: n*10000, 0x286d: n*10000, 0x28a4: n*1000, 0x28ee: n*1000, 0x28ef: n*1000}.get(code, g)
        if code in (0x1d9e, 0x1db8) and it['period'] == 1 and it['expired'] == 1 and gt == 1:
            g = 0
        if ka(0x20) or code in (0x289d, 0x2610, 0x291f):
            g = 0
        g = {0x2876: 10000, 0x289e: n*10000, 0x289f: 10000, 0x28a0: 10000, 0x28a1: n*1000}.get(code, g)
        own = self.records.get(code)
        if own is not None and own[0x250] == 0x22:
            g = 50000
        if code in (0x181d, 0x1a06) or 0x2984 <= code <= 0x2987:
            g = 0
        if gt == 1 and code in (0x1a10, 0x1a11, 0x1a12, 0x1c11, 0x1c12, 0x1c13, 0x1a31, 0x1a32, 0x1a33, 0x1a1d,
                                0x1c6e, 0x1c6f, 0x286c, 0x286d, 0x1dae):
            g = 0
        ban = kb(0x2b) or (it['period'] == 1 and it['expired'] == 1) or r[0x2ae] == 0
        if not ban and gt == 1:
            md = it['max_durability']
            worn = f32(1.0 - f32(n/md)) if md else (f32(1.0 - math.inf) if n else math.nan)
            cut = dtol(f32(f32(f32(float(g))*f32(0.6))*worn)) & 0xffffffff
            if code == 0x1a1f:
                cut = 0
            g = i64(g - cut)
        return g

    @staticmethod
    def repair(value, durability, maximum, code, shop=0, flag=0, inventory=0, discount=0):
        gold = min(value, 400000000)
        rg = f32(float(gold))
        worn = f32(1.0 - f32(durability/maximum)) if maximum else (f32(1.0 - math.inf) if durability else math.nan)
        if worn > 0:
            a = f32(math.sqrt(rg))
            b = f32(math.sqrt(math.sqrt(rg)))
            rg = f32(f32(f32(3.0*a)*b)*worn)
            rg = f32(rg + 1.0)
            if durability <= 0:
                rg = f32(rg*2.0) if code in (0x1a04, 0x1a05, 0x28f7, 0x28f8, 0x28f9, 0x28fa, 0x2900) \
                    else f32(f32(rg*f32(0.4)) + rg)
        else:
            rg = 0.0
        if inventory and not (shop and flag):
            rg = f32(f32(rg*f32(1.1)) + rg)
        gold = math.trunc(rg) if -2.0**31 <= rg < 2.0**31 else -(1 << 31)
        if gold >= 1000:
            gold = tdiv(gold, 100)*100
        elif gold >= 100:
            gold = tdiv(gold, 10)*10
        return i32(gold - i32(tdiv(gold*discount, 100)))


def blank():
    return {'code': -1, 'level': 0, 'durability': 0, 'max_durability': 0, 'set_bits': 0, 'special_count': 0,
            'special': [0]*8, 'special_value': [0]*8, 'skill': 0, 'flag_72': 0, 'slot_73': [0]*5,
            'socket_count': 0, 'socket': [0]*5, 'socket_level': [0]*5, 'period': 0, 'expired': 0, 'excellent': 0,
            'excellent_options': [0xff]*9, 'harmony': 0}


def to_c(it):
    c = Item()
    for k, v in it.items():
        if isinstance(v, list):
            arr = getattr(c, k)
            for i, x in enumerate(v):
                arr[i] = x
        else:
            setattr(c, k, v)
    return c


class Native:
    def __init__(self, records, seeds, soul):
        lib = self.lib = ctypes.CDLL(str(LIB))
        lib.mu_item_price.argtypes = [ctypes.c_char_p, ctypes.POINTER(Item), ctypes.c_int, ctypes.POINTER(State)]
        lib.mu_item_price.restype = ctypes.c_int32
        lib.mu_item_repair_cost.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int16,
                                            ctypes.POINTER(Repair)]
        lib.mu_item_repair_cost.restype = ctypes.c_int32
        lib.mu_price_format.argtypes = [ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t]
        lib.mu_price_format.restype = ctypes.c_char_p
        lib.mu_price_item_init.argtypes = [ctypes.POINTER(Item)]
        self.buffers = {code: ctypes.create_string_buffer(bytes(r), len(r)) for code, r in records.items()}
        self.seeds = (ctypes.c_int32*256)(*seeds)
        self.record_of = RECORD_OF(lambda u, code: ctypes.addressof(self.buffers[code]) if code in self.buffers else None)
        self.soul_of = SOUL_OF(lambda u, code: int(code in soul))

    def price(self, record, it, gt, world=0, flag=0, pet=(-1, 0)):
        state = State(world, flag, self.seeds, self.record_of, self.soul_of, None, pet[0], pet[1])
        return self.lib.mu_item_price(bytes(record), ctypes.byref(to_c(it)), gt, ctypes.byref(state))


def synthetic(rng, code):
    r = bytearray(rng.randrange(256) for _ in range(708))
    struct.pack_into('<i', r, 0, code)
    mode = rng.randrange(6)
    if mode:
        r[0x28c:0x290] = bytes(4)
    if mode >= 2:
        r[0x288] = 0
    if mode == 3:
        r[0x250] = rng.choice([2, 6, 9, 0xb, 0xc, 0x17, 0x19, 0x1a, 0x1c, 0x20, 0x22, 0x2d, 0x2e, 0x38, 0xe])
        r[0x251] = rng.choice([0, 0x16, 0x2b, 0x2c, 0x5c, 0x64, 7])
        r[0x252] = rng.choice([0, 2, 4, 5, 1])
    if mode >= 4:
        r[0x250], r[0x251], r[0x252] = rng.randrange(8), rng.randrange(0x20), rng.choice([0, 1, 2, 3])
        r[0x2af] = r[0x2b0] = r[0x2b1] = 0
    return bytes(r)


def random_item(rng, code):
    it = blank()
    it.update(code=code, level=rng.randrange(16), durability=rng.randrange(256),
              max_durability=rng.choice([0, rng.randrange(256), 255]), set_bits=rng.choice([0, 1, 0x10, 0x40]),
              special_count=rng.randrange(5), skill=rng.choice([0, 0x12, 0x38, 0x10e, 7]),
              flag_72=rng.choice([0, 1, 2]), socket_count=rng.choice([0, 1, 3, 5]),
              period=rng.randrange(2), expired=rng.randrange(2), excellent=rng.choice([0, 1, 2]),
              harmony=rng.choice([0, rng.randrange(20)]))
    it['special'] = [rng.choice([0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 13]) for _ in range(8)]
    it['special_value'] = [rng.choice([1, 2, 3, 4, 5, 8, 10, 12, 15, 16, 20, 7]) for _ in range(8)]
    it['slot_73'] = [rng.choice([0xff, rng.randrange(256)]) for _ in range(5)]
    it['socket'] = [rng.choice([0xff, rng.randrange(8)]) for _ in range(5)]
    it['socket_level'] = [rng.randrange(1, 11) for _ in range(5)]
    k = rng.choice([0, 0, 1, 3, 9])
    it['excellent_options'] = [rng.randrange(255) if i < k else 0xff for i in range(9)]
    return it


class PriceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(HERE)], check=True)
        rng = random.Random(0x4c32)
        cls.records = {}
        for code in list(range(0x1864, 0x1882)) + list(range(0x1937, 0x1955)):   # seed spheres
            r = bytearray(708)
            struct.pack_into('<i', r, 0, code)
            r[0x288] = rng.randrange(1, 40)
            cls.records[code] = bytes(r)
        cls.seeds = [rng.randrange(1, 7) for _ in range(256)]
        cls.soul = {0x1c0d, 0x0005}
        cls.native = Native(cls.records, cls.seeds, cls.soul)
        cls.model = Model(cls.records, cls.seeds, cls.soul)

    def test_random_states_agree_with_the_statement(self):
        rng = random.Random(7)
        codes = [rng.randrange(0x2c00) for _ in range(300)] + [
            0x807, 0x80f, 0x1c0d, 0x1c10, 0x1a03, 0x1a10, 0x1a12, 0x1c11, 0x1c13, 0x1a31, 0x1c09, 0x1c07, 0x1a07,
            0x1c23, 0x1920, 0x1897, 0x1c00, 0x1c05, 0x1a14, 0x1a1f, 0x1a20, 0x1c9d, 0x1a04, 0x1a70, 0x1886, 0x20ef,
            0x1d59, 0x1dd4, 0x2985, 0x29, -1, -3, 0x2c01]
        checked = 0
        for code in codes:
            for _ in range(12):
                r = synthetic(rng, code)
                it = random_item(rng, code)
                gt, world, flag = rng.randrange(3), rng.choice([0, 0x5c]), int(rng.random() < 0.05)
                pet = (rng.choice([-1, 0, 1]), rng.randrange(1 << 32))
                want = self.model.value(r, it, gt, world, flag, pet)
                got = self.native.price(r, it, gt, world, flag, pet)
                self.assertEqual(got, want, (hex(code), it, gt, world, flag))
                checked += 1
        self.assertGreater(checked, 3900)

    def test_worked_examples(self):
        r = bytearray(708)
        struct.pack_into('<i', r, 0x28c, 1234)           # a fixed price
        it = blank()
        it['code'] = 0x0e00
        self.assertEqual(self.native.price(r, it, 0), 1200)        # >= 1000: to hundreds
        self.assertEqual(self.native.price(r, it, 1), 410)         # sell: a third, to tens
        r[0x2af], it['durability'] = 20, 7                          # stackable: times the stack
        self.assertEqual(self.native.price(r, it, 0), 8400)
        self.assertEqual(self.native.price(r, it, 1, flag=1), 1)   # the singleton's sell flag
        it['code'] = -1
        self.assertEqual(self.native.price(r, it, 0), 0)
        r = bytearray(708)
        r[0x254], r[0x253], r[0x2ae] = 6, 1, 1                      # Kris-like: level 6, one-handed flag set
        it = blank()
        it.update(code=0x0000 + 1, level=0, durability=20, max_durability=20)
        # lvl 6: (46 * 6 * 6) / 8 + 100 = 307; record +0x253 != 0 keeps it; tail rounds to 300
        self.assertEqual(self.native.price(r, it, 0), 300)
        self.assertEqual(self.native.price(r, it, 1), 100)         # 307 / 3 = 102 -> 100 (full durability)
        it['durability'] = 10                                       # half worn: 102 - (int)(102*0.6*0.5) = 72
        self.assertEqual(self.native.price(r, it, 1), 72)          # below 100: no rounding
        pet = blank()
        pet['code'] = 0x1a04
        self.assertEqual(self.native.price(bytes(708), pet, 0, pet=(-1, 0)), -1)
        self.assertEqual(self.native.price(bytes(708), pet, 0, pet=(1, 4567)), 4500)

    def test_repair_cost(self):
        rng = random.Random(11)
        lib = self.native.lib
        for _ in range(4000):
            value = rng.choice([0, 1, 150, 999, 1000, rng.randrange(1 << 24), rng.randrange(1 << 31), 400000001])
            maximum = rng.choice([0, 1, rng.randrange(256)])
            durability = rng.choice([0, maximum, rng.randrange(256)])
            code = rng.choice([0x1a04, 0x1a06, rng.randrange(0x2c00)])
            window = (rng.randrange(2), rng.randrange(2), rng.randrange(2), rng.choice([0, 5, 37]))
            got = lib.mu_item_repair_cost(value, durability, maximum, code, ctypes.byref(Repair(*window)))
            self.assertEqual(got, Model.repair(value, durability, maximum, code, *window),
                             (value, durability, maximum, hex(code), window))
        # full durability costs nothing; 400 zen at 5/10: 3 * 20 * 4.472 * 0.5 + 1 = 135.2 -> 130
        self.assertEqual(lib.mu_item_repair_cost(400, 10, 10, 1, None), 0)
        self.assertEqual(lib.mu_item_repair_cost(400, 5, 10, 1, None), 130)

    def test_format(self):
        buf = ctypes.create_string_buffer(32)
        for value, text in ((0, b'0'), (999, b'999'), (1000, b'1,000'), (1234567, b'1,234,567'),
                            (4000000000, b'4,000,000,000')):
            self.assertEqual(self.native.lib.mu_price_format(value, buf, 32), text)

    def test_init_is_a_constructed_object(self):
        c = Item()
        self.native.lib.mu_price_item_init(ctypes.byref(c))
        self.assertEqual(c.code, -1)
        self.assertEqual(list(c.excellent_options), [0xff]*9)
        self.assertEqual(c.harmony, 0)


if __name__ == '__main__':
    unittest.main()
