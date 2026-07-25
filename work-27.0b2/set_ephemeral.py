#!/usr/bin/env python3
import sys
f=sys.argv[1]
d=bytearray(open(f,'rb').read())
key=b"ephemeral-storage\x00"
i=d.find(key)
if i<0: print("ephemeral-storage NOT found!"); sys.exit(1)
lenoff=i+32; vlen=int.from_bytes(d[lenoff:lenoff+4],'little')&0x7fffffff; voff=lenoff+4
old=d[voff:voff+4].hex()
d[voff:voff+4]=(1).to_bytes(4,'little')
open(f,'wb').write(d)
print(f"[+] ephemeral-storage: {old} -> 01000000 (name_off={hex(i)} val_off={hex(voff)} vlen={vlen})")
