#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dt_content_protect.py — toggle the /defaults/content-protect flag in an
Apple flattened DeviceTree (iBoot DTB). Based on dt_patch.py.

IMPORTANT: content-protect is a ZERO-LENGTH flag property. Its PRESENCE
(not any value) is what matters — restored_external's DataEncryptionType
accessor only checks whether the property EXISTS:
    present  -> content protection ON  (enum 2, encrypted)
    absent   -> "content-protect property not found" path (unencrypted)

So "changing" content-protect means REMOVING it (disable) or ADDING it
(re-enable) — not setting a value. This script re-serializes the whole tree
losslessly (property removal shifts bytes) and verifies the result.

Apple DT binary layout (little-endian):
    Node:      uint32 nProperties; uint32 nChildren; Property*; Node*   (recursive)
    Property:  char name[32]; uint32 length (bit31 = placeholder flag);
               uint8 value[length]  (padded to a 4-byte boundary)
    (a node's own name is a property literally called "name")

Usage:
    python3 dt_content_protect.py DeviceTree.raw                 # remove (disable) [default]
    python3 dt_content_protect.py DeviceTree.raw --enable        # add it back (zero-length)
    python3 dt_content_protect.py DeviceTree.raw -o out.raw
    python3 dt_content_protect.py DeviceTree.raw --dry-run
    python3 dt_content_protect.py DeviceTree.raw --list          # show crypto-related props
"""

import sys
import os
import struct
import argparse

FLAG_PLACEHOLDER = 0x80000000
NAME_LEN = 32
PROP_NAME = "content-protect"
DEFAULT_NODE = "/defaults"


def _align4(x: int) -> int:
    return (x + 3) & ~3


class Prop:
    __slots__ = ("name_raw", "raw_lenfield", "value")

    def __init__(self, name_raw: bytes, raw_lenfield: int, value: bytes):
        assert len(name_raw) == NAME_LEN
        self.name_raw = name_raw          # exact 32 bytes (lossless)
        self.raw_lenfield = raw_lenfield  # includes flag bits
        self.value = value                # exactly `length` bytes

    @property
    def name(self) -> str:
        return self.name_raw.split(b"\x00")[0].decode("ascii", "replace")

    @property
    def flags(self) -> int:
        return self.raw_lenfield & FLAG_PLACEHOLDER

    @property
    def length(self) -> int:
        return self.raw_lenfield & 0x7FFFFFFF

    @staticmethod
    def make(name: str, value: bytes = b"", flags: int = 0) -> "Prop":
        nr = name.encode("ascii")
        if len(nr) >= NAME_LEN:
            raise ValueError("property name too long")
        nr = nr + b"\x00" * (NAME_LEN - len(nr))
        return Prop(nr, (flags & FLAG_PLACEHOLDER) | (len(value) & 0x7FFFFFFF), bytes(value))

    def serialize(self) -> bytes:
        out = bytearray()
        out += self.name_raw
        out += struct.pack("<I", self.raw_lenfield)
        out += self.value
        out += b"\x00" * (_align4(len(self.value)) - len(self.value))
        return bytes(out)


class Node:
    __slots__ = ("props", "children")

    def __init__(self):
        self.props = []      # list[Prop]
        self.children = []   # list[Node]

    @property
    def name(self) -> str:
        for p in self.props:
            if p.name == "name":
                return p.value.split(b"\x00")[0].decode("ascii", "replace")
        return ""

    def serialize(self) -> bytes:
        out = bytearray()
        out += struct.pack("<II", len(self.props), len(self.children))
        for p in self.props:
            out += p.serialize()
        for c in self.children:
            out += c.serialize()
        return bytes(out)


class AppleDeviceTree:
    def __init__(self):
        self.root = None

    @classmethod
    def parse(cls, data: bytes) -> "AppleDeviceTree":
        dt = cls()
        off, dt.root = cls._parse_node(data, 0)
        if off != len(data):
            sys.stderr.write(
                f"[warn] parsed {off:#x} but file is {len(data):#x} bytes "
                f"({len(data) - off} trailing bytes)\n"
            )
        return dt

    @staticmethod
    def _parse_node(data: bytes, off: int):
        nprops, nchildren = struct.unpack_from("<II", data, off)
        o = off + 8
        node = Node()
        for _ in range(nprops):
            name_raw = data[o:o + NAME_LEN]
            (raw_len,) = struct.unpack_from("<I", data, o + NAME_LEN)
            rlen = raw_len & 0x7FFFFFFF
            voff = o + NAME_LEN + 4
            node.props.append(Prop(name_raw, raw_len, data[voff:voff + rlen]))
            o = voff + _align4(rlen)
        for _ in range(nchildren):
            o, child = AppleDeviceTree._parse_node(data, o)
            node.children.append(child)
        return o, node

    def serialize(self) -> bytes:
        return self.root.serialize()

    @staticmethod
    def _norm(path: str) -> str:
        p = "/" + path.strip("/")
        if p.startswith("/device-tree/"):
            p = p[len("/device-tree"):]
        elif p == "/device-tree":
            p = "/"
        return p

    def _walk(self):
        def rec(node, path):
            yield path, node
            for c in node.children:
                cname = c.name or "(anon)"
                cpath = "/" + cname if path == "/" else path + "/" + cname
                yield from rec(c, cpath)
        yield from rec(self.root, "/")

    def find_node(self, path: str):
        target = self._norm(path)
        for p, node in self._walk():
            if p == target:
                return node
        return None

    def find_prop_anywhere(self, prop_name: str):
        """Return (path, node, prop) for the first matching property, or None."""
        for path, node in self._walk():
            for p in node.props:
                if p.name == prop_name:
                    return path, node, p
        return None

    def remove_prop(self, node, prop_name: str) -> bool:
        for i, p in enumerate(node.props):
            if p.name == prop_name:
                del node.props[i]
                return True
        return False

    def add_prop(self, node_path: str, prop: Prop) -> bool:
        node = self.find_node(node_path)
        if node is None:
            return False
        node.props.append(prop)
        return True


# ------------------------------------------------------------------ CLI

CRYPTO_PROPS = {
    "content-protect", "cpx-encryption-mode", "protected-data-access",
    "sepfw-load-at-boot", "disable-av-content-protection",
}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Toggle /defaults/content-protect in an Apple DeviceTree (iBoot DTB).")
    ap.add_argument("input", help="DeviceTree.raw (unwrapped IM4P payload)")
    ap.add_argument("-o", "--output", help="output path (default: <input>.patched)")
    ap.add_argument("--enable", action="store_true",
                    help="ADD content-protect (zero-length) instead of removing it")
    ap.add_argument("--node", default=DEFAULT_NODE,
                    help=f"node to add to when --enable (default: {DEFAULT_NODE})")
    ap.add_argument("--list", action="store_true",
                    help="print crypto-related properties and exit")
    ap.add_argument("--dry-run", action="store_true", help="show change, do not write")
    ap.add_argument("--no-verify", action="store_true", help="skip round-trip verification")
    args = ap.parse_args(argv)

    data = open(args.input, "rb").read()
    dt = AppleDeviceTree.parse(data)

    # lossless round-trip sanity on the untouched tree
    if not args.no_verify and dt.serialize() != data:
        sys.stderr.write("[warn] lossless round-trip mismatch before edits — format quirk\n")

    if args.list:
        print("crypto-related properties in tree:")
        for path, node in dt._walk():
            for p in node.props:
                if p.name in CRYPTO_PROPS:
                    u32 = int.from_bytes(p.value, "little") if p.length == 4 else None
                    extra = f" u32={u32}" if u32 is not None else " (zero-length flag)" if p.length == 0 else ""
                    print(f"  {path}/{p.name:30s} len={p.length}{extra}")
        return 0

    found = dt.find_prop_anywhere(PROP_NAME)

    if args.enable:
        # ADD the flag (zero-length) if not already present
        if found:
            print(f"[=] {PROP_NAME} already present at {found[0]} — nothing to do")
            return 0
        prop = Prop.make(PROP_NAME, value=b"", flags=0)  # zero-length flag
        if not dt.add_prop(args.node, prop):
            sys.exit(f"[err] node not found: {AppleDeviceTree._norm(args.node)}")
        print(f"[+] added {PROP_NAME} (zero-length) to {AppleDeviceTree._norm(args.node)}")
    else:
        # REMOVE the flag (disable content protection)
        if not found:
            print(f"[=] {PROP_NAME} not present — content protection already off; nothing to do")
            return 0
        path, node, prop = found
        if prop.length != 0:
            sys.stderr.write(
                f"[warn] {PROP_NAME} is {prop.length} bytes (expected zero-length flag); "
                f"removing anyway\n")
        dt.remove_prop(node, PROP_NAME)
        print(f"[-] removed {PROP_NAME} from {path} "
              f"(was len={prop.length}, {node.__class__.__name__} now has {len(node.props)} props)")

    out_bytes = dt.serialize()

    if args.dry_run:
        print(f"\n[dry-run] not writing. new size = {len(out_bytes)} (was {len(data)})")
        return 0

    out_path = args.output or (args.input + ".patched")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(out_bytes)
    print(f"\n[+] wrote {out_path} ({len(out_bytes)} bytes, was {len(data)})")

    # verify
    if not args.no_verify:
        dt2 = AppleDeviceTree.parse(out_bytes)
        still = dt2.find_prop_anywhere(PROP_NAME)
        if args.enable:
            ok = still is not None
            print(f"    verify: {PROP_NAME} present = {ok}  [{'OK' if ok else 'FAIL'}]")
        else:
            ok = still is None
            print(f"    verify: {PROP_NAME} absent = {ok}  [{'OK' if ok else 'FAIL'}]")
        # a removed zero-length prop shrinks the file by exactly 36 bytes (32 name + 4 len)
        delta = len(data) - len(out_bytes)
        print(f"    size delta: {delta:+d} bytes")
        if not ok:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())