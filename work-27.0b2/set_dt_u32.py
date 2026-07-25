#!/usr/bin/env python3
# Set a u32 DeviceTree bool/scalar property in a raw DeviceTree.
# Apple DT property layout: char name[32]; u32 length(top bit=flags); value...
# Usage: ./set_dt_u32.py <DeviceTree.raw> <prop-name> <value>
import sys
f, name, val = sys.argv[1], sys.argv[2], int(sys.argv[3], 0)
d = bytearray(open(f, 'rb').read())
key = name.encode() + b"\x00"
i = d.find(key)
if i < 0:
    print(f"[!] {name} NOT found!"); sys.exit(1)
lenoff = i + 32
vlen = int.from_bytes(d[lenoff:lenoff+4], 'little') & 0x7fffffff
voff = lenoff + 4
if vlen != 4:
    print(f"[!] {name} at {hex(i)} has len={vlen} (not a u32 property); refusing"); sys.exit(1)
old = d[voff:voff+4].hex()
d[voff:voff+4] = val.to_bytes(4, 'little')
open(f, 'wb').write(d)
print(f"[+] {name}: {old} -> {d[voff:voff+4].hex()} (name_off={hex(i)} val_off={hex(voff)})")
