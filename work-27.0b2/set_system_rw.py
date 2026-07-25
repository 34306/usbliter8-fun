#!/usr/bin/env python3
# Đổi vol.fs_type của volume "System" (rootfs, fs_file=/) từ 'ro' -> 'rw' trong DeviceTree raw.
# Nhắm chính xác: tìm property vol.fs_name có value 'System', rồi lấy vol.fs_type GẦN NHẤT
# đứng TRƯỚC nó (trong cùng descriptor) -> set 'rw'. Không đụng các entry ro khác (Preboot...).
# DT prop layout: char name[32]; u32 len(top bit=flags); value[len].
import sys
f = sys.argv[1] if len(sys.argv) > 1 else "DeviceTree_patched.raw"
d = bytearray(open(f, "rb").read())

def prop_val_off(name_off):
    lo = name_off + 32
    vlen = int.from_bytes(d[lo:lo+4], "little") & 0x7fffffff
    return lo + 4, vlen

# 1) tìm vol.fs_name == 'System'
sys_name_off = -1
s = 0
key = b"vol.fs_name\x00"
while True:
    i = d.find(key, s)
    if i < 0: break
    vo, vlen = prop_val_off(i)
    if d[vo:vo+vlen].split(b"\x00")[0] == b"System":
        sys_name_off = i; break
    s = i + 1
if sys_name_off < 0:
    print("[!] không tìm thấy volume 'System'"); sys.exit(1)

# 2) vol.fs_type gần nhất TRƯỚC vol.fs_name='System'
tkey = b"vol.fs_type\x00"
best = -1; s = 0
while True:
    i = d.find(tkey, s)
    if i < 0 or i > sys_name_off: break
    best = i; s = i + 1
if best < 0:
    print("[!] không tìm thấy vol.fs_type của System"); sys.exit(1)

vo, vlen = prop_val_off(best)
old = d[vo:vo+vlen].split(b"\x00")[0].decode()
if old == "rw":
    print(f"[=] System vol.fs_type đã là 'rw' (off={hex(best)}), bỏ qua"); sys.exit(0)
if old != "ro":
    print(f"[!] System vol.fs_type = {old!r} (không phải 'ro'); refuse"); sys.exit(1)
# 'ro' -> 'rw' cùng độ dài (r o \0 -> r w \0)
d[vo:vo+3] = b"rw\x00"
open(f, "wb").write(d)
print(f"[+] System vol.fs_type: 'ro' -> 'rw' (name_off={hex(sys_name_off)} type_off={hex(best)} val_off={hex(vo)})")
