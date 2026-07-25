#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dt_patch.py — apply QEMU-t8030-style DeviceTree patches to an Apple
flattened DeviceTree (unwrapped IM4P payload), matching xnu.c
(macho_populate_dtb + REM_PROPS in macho_dtb_node_process).

Patches applied (each mirrors an exact line in xnu.c):
    del-prop  /defaults/content-protect            REM_PROPS: no encrypted data volume
    set  u32=1 /defaults/no-effaceable-storage      AppleKeyStore SEP workaround
    set  u32=1 /product/boot-ios-diagnostics        AppleKeyStore SEP workaround

Semantics mirror the QEMU DTB helpers:
    set-prop  -> set_dtb_prop     : overwrite value if present, else append
    del-prop  -> remove_dtb_prop  : drop a property

Binary layout (little-endian):
    Node:  u32 nprops; u32 nchildren; Prop*; Node*      (recursive)
    Prop:  char name[32]; u32 length (bit31 = placeholder flag);
           u8 value[length]  (padded to a 4-byte boundary)
    (a node's own name is a property literally called "name")

Usage:
    python3 dt_patch.py DeviceTree.raw                 # -> DeviceTree.raw.patched
    python3 dt_patch.py DeviceTree.raw -o out.raw
    python3 dt_patch.py DeviceTree.raw --dry-run
"""

import sys
import os
import struct
import argparse

FLAG_PLACEHOLDER = 0x80000000
NAME_LEN = 32


def _align4(x):
    return (x + 3) & ~3


class Prop:
    __slots__ = ("name_raw", "raw_lenfield", "value")

    def __init__(self, name_raw, raw_lenfield, value):
        self.name_raw = name_raw          # exact 32 bytes (lossless)
        self.raw_lenfield = raw_lenfield  # low 31 bits = length, bit31 = flag
        self.value = value

    @property
    def name(self):
        return self.name_raw.split(b"\x00")[0].decode("ascii", "replace")

    @property
    def length(self):
        return self.raw_lenfield & 0x7FFFFFFF

    @property
    def flags(self):
        return self.raw_lenfield & FLAG_PLACEHOLDER

    def set_value(self, value):
        # overwrite value, preserve the placeholder flag (set_dtb_prop update path)
        self.value = bytes(value)
        self.raw_lenfield = self.flags | (len(value) & 0x7FFFFFFF)

    @staticmethod
    def make(name, value=b""):
        nr = name.encode("ascii")
        assert len(nr) < NAME_LEN, "property name too long"
        nr += b"\x00" * (NAME_LEN - len(nr))
        return Prop(nr, len(value) & 0x7FFFFFFF, bytes(value))

    def serialize(self):
        v = self.value
        return (self.name_raw + struct.pack("<I", self.raw_lenfield)
                + v + b"\x00" * (_align4(len(v)) - len(v)))


class Node:
    __slots__ = ("props", "children")

    def __init__(self):
        self.props = []
        self.children = []

    @property
    def name(self):
        for p in self.props:
            if p.name == "name":
                return p.value.split(b"\x00")[0].decode("ascii", "replace")
        return ""

    def prop(self, name):
        return next((p for p in self.props if p.name == name), None)

    def child(self, name):
        return next((c for c in self.children if c.name == name), None)

    def serialize(self):
        out = bytearray(struct.pack("<II", len(self.props), len(self.children)))
        for p in self.props:
            out += p.serialize()
        for c in self.children:
            out += c.serialize()
        return bytes(out)


class DeviceTree:
    def __init__(self, root):
        self.root = root

    @classmethod
    def parse(cls, data):
        off, root = cls._node(data, 0)
        if off != len(data):
            sys.stderr.write(f"[warn] {len(data) - off} trailing bytes after parse\n")
        return cls(root)

    @staticmethod
    def _node(data, o):
        nprops, nchildren = struct.unpack_from("<II", data, o)
        o += 8
        node = Node()
        for _ in range(nprops):
            name_raw = data[o:o + NAME_LEN]
            (rlf,) = struct.unpack_from("<I", data, o + NAME_LEN)
            vlen = rlf & 0x7FFFFFFF
            voff = o + NAME_LEN + 4
            node.props.append(Prop(name_raw, rlf, data[voff:voff + vlen]))
            o = voff + _align4(vlen)
        for _ in range(nchildren):
            o, c = DeviceTree._node(data, o)
            node.children.append(c)
        return o, node

    def serialize(self):
        return self.root.serialize()

    def node(self, path):
        """Resolve '/a/b/c' by walking child nodes by name (root = tree root)."""
        n = self.root
        for part in path.strip("/").split("/"):
            if not part:
                continue
            n = n.child(part)
            if n is None:
                return None
        return n


# ---- patch primitives (mirror the QEMU DTB helpers) ------------------------

def set_prop(dt, node_path, name, value):
    n = dt.node(node_path)
    if n is None:
        sys.exit(f"[err] node not found: {node_path}")
    p = n.prop(name)
    if p is None:
        n.props.append(Prop.make(name, value))
        return "added"
    if p.value == bytes(value):
        return "unchanged"
    p.set_value(value)
    return "updated"


def del_prop(dt, node_path, name):
    n = dt.node(node_path)
    if n is None:
        sys.exit(f"[err] node not found: {node_path}")
    p = n.prop(name)
    if p is None:
        return "absent"
    n.props.remove(p)
    return "removed"


# ---- patch table (each row == one line in xnu.c) ---------------------------

U32_1 = struct.pack("<I", 1)

#         (op,        node path,      prop name,                value)
PATCHES = [
    ("del-prop", "/defaults", "content-protect",       None),
    ("set-prop", "/defaults", "no-effaceable-storage", U32_1),
    ("set-prop", "/product",  "boot-ios-diagnostics",  U32_1),
]

_OPS = {"set-prop": set_prop, "del-prop": del_prop}


def apply_patches(dt):
    report = []
    for op, path, name, value in PATCHES:
        args = (dt, path, name, value) if op == "set-prop" else (dt, path, name)
        report.append((op, f"{path}/{name}", _OPS[op](*args)))
    return report


def verify(data):
    """Re-parse output bytes and confirm every patch reached its end state."""
    dt = DeviceTree.parse(data)
    ok = True
    for op, path, name, value in PATCHES:
        n = dt.node(path)
        p = n.prop(name) if n else None
        good = (p is None) if op == "del-prop" else (p is not None and p.value == value)
        ok &= good
        print(f"    verify {op:8s} {path}/{name:24s} [{'OK' if good else 'FAIL'}]")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Apply xnu.c DeviceTree patches to an Apple DTB (unwrapped IM4P).")
    ap.add_argument("input", help="DeviceTree.raw")
    ap.add_argument("-o", "--output", help="output path (default: <input>.patched)")
    ap.add_argument("--dry-run", action="store_true", help="show changes, do not write")
    args = ap.parse_args(argv)

    data = open(args.input, "rb").read()
    dt = DeviceTree.parse(data)
    if dt.serialize() != data:
        sys.stderr.write("[warn] lossless round-trip mismatch before edits — format quirk\n")

    for op, target, status in apply_patches(dt):
        print(f"[{op:8s}] {target:34s} {status}")

    out = dt.serialize()
    print(f"\nsize: {len(data)} -> {len(out)} ({len(out) - len(data):+d} bytes)")

    if args.dry_run:
        print("[dry-run] not writing.")
        return 0

    out_path = args.output or (args.input + ".patched")
    d = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(d, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(out)
    print(f"[+] wrote {out_path}")

    return 0 if verify(out) else 1


if __name__ == "__main__":
    sys.exit(main())
