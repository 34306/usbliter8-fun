#!/usr/bin/env python3.14
# -*- coding: utf-8 -*-
"""
dt_patch.py — Apple flattened DeviceTree (iBoot DTB) property patcher.

This parses the Apple "device tree" binary format (the one iBoot loads and XNU
exposes as IODeviceTree — NOT the Linux FDT/dtb format), lets you set property
values by node-path + property-name, re-serializes losslessly, and verifies the
round-trip.

Apple DT binary layout (little-endian):

    Node:
        uint32  nProperties
        uint32  nChildren
        Property * nProperties
        Node     * nChildren            # recursive

    Property:
        char     name[32]               # NUL-padded
        uint32   length                 # bit31 (0x80000000) = placeholder flag
        uint8    value[length]          # padded up to a 4-byte boundary

A node's own name is stored as a property literally called "name".

Default action (no --set / --u32 given): turn OFF SEP fw load + data protection
    /chosen/sepfw-load-at-boot    -> 0
    /chosen/protected-data-access -> 0
(Both kept present and 4 bytes wide so AMFI's "no node" / "unexpected size"
 panics are avoided.)

Examples:
    # defaults (both SEP/data-protection props -> 0)
    python3 dt_patch.py DeviceTree.raw -o DeviceTree.patched.raw

    # arbitrary u32
    python3 dt_patch.py DeviceTree.raw --u32 /chosen/sepfw-load-at-boot=0 \
                                        --u32 /chosen/protected-data-access=0

    # arbitrary raw hex bytes
    python3 dt_patch.py DeviceTree.raw --set /chosen/foo=deadbeef

    # inspect a node without writing
    python3 dt_patch.py DeviceTree.raw --list /chosen --dry-run
"""

import sys
import os
import struct
import argparse

FLAG_PLACEHOLDER = 0x80000000
NAME_LEN = 32


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

    def set_value(self, new_value: bytes):
        """Replace value, preserving flag bits, updating the length field."""
        self.value = bytes(new_value)
        self.raw_lenfield = self.flags | (len(self.value) & 0x7FFFFFFF)

    def serialize(self) -> bytes:
        out = bytearray()
        out += self.name_raw
        out += struct.pack("<I", self.raw_lenfield)
        out += self.value
        pad = _align4(len(self.value)) - len(self.value)
        out += b"\x00" * pad
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
        return ""  # root has name "device-tree"; unnamed otherwise

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

    # ---- parsing ---------------------------------------------------------
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
            value = data[voff:voff + rlen]
            node.props.append(Prop(name_raw, raw_len, value))
            o = voff + _align4(rlen)
        for _ in range(nchildren):
            o, child = AppleDeviceTree._parse_node(data, o)
            node.children.append(child)
        return o, node

    def serialize(self) -> bytes:
        return self.root.serialize()

    # ---- lookup ----------------------------------------------------------
    @staticmethod
    def _norm(path: str) -> str:
        # accept "chosen", "/chosen", "/device-tree/chosen"
        p = "/" + path.strip("/")
        if p.startswith("/device-tree/"):
            p = p[len("/device-tree"):]
        elif p == "/device-tree":
            p = "/"
        return p

    def _walk(self):
        """Yield (path, node) for every node, root path == '/'."""
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

    def find_prop(self, node_path: str, prop_name: str):
        node = self.find_node(node_path)
        if node is None:
            return None
        for p in node.props:
            if p.name == prop_name:
                return p
        return None

    def set_prop(self, node_path: str, prop_name: str, value: bytes) -> bool:
        p = self.find_prop(node_path, prop_name)
        if p is None:
            return False
        p.set_value(value)
        return True


# ------------------------------------------------------------------ CLI

def _parse_kv(s: str):
    if "=" not in s:
        raise argparse.ArgumentTypeError(f"expected PATH/PROP=VALUE, got {s!r}")
    left, val = s.rsplit("=", 1)
    left = left.strip()
    # split the property name off the trailing path component
    node_path, _, prop = left.rpartition("/")
    if not prop:
        raise argparse.ArgumentTypeError(f"missing property name in {s!r}")
    if not node_path:
        node_path = "/"
    return node_path, prop, val.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Patch Apple DeviceTree (iBoot DTB) properties.")
    ap.add_argument("input", help="DeviceTree.raw (unwrapped IM4P payload)")
    ap.add_argument("-o", "--output", help="output path (default: <input>.patched)")
    ap.add_argument("--set", action="append", default=[], metavar="PATH/PROP=HEX",
                    help="set property to raw hex bytes (repeatable)")
    ap.add_argument("--u32", action="append", default=[], metavar="PATH/PROP=N",
                    help="set property to a little-endian u32 (repeatable)")
    ap.add_argument("--list", metavar="PATH",
                    help="print all properties of the given node and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="show changes but do not write output")
    ap.add_argument("--no-verify", action="store_true",
                    help="skip re-parse/round-trip verification")
    args = ap.parse_args(argv)

    data = open(args.input, "rb").read()
    dt = AppleDeviceTree.parse(data)

    # round-trip sanity on the untouched tree (proves lossless parser)
    if not args.no_verify:
        rt = dt.serialize()
        if rt != data:
            sys.stderr.write(
                f"[warn] lossless round-trip mismatch before edits "
                f"(orig {len(data):#x} vs {len(rt):#x}) — padding/format quirk\n"
            )

    if args.list:
        node = dt.find_node(args.list)
        if node is None:
            sys.exit(f"[err] node not found: {args.list}")
        print(f"# {AppleDeviceTree._norm(args.list)}  "
              f"({len(node.props)} props, {len(node.children)} children)")
        for p in node.props:
            head = p.value[:32].hex()
            extra = ""
            if p.length == 4:
                extra = f"  u32={struct.unpack('<I', p.value)[0]}"
            flag = " [PLACEHOLDER]" if p.flags else ""
            print(f"  {p.name:30s} len={p.length:<5} {head}{extra}{flag}")
        return 0

    # build the edit list
    edits = []  # (node_path, prop, value_bytes, human)
    for kv in args.set:
        np_, prop, val = _parse_kv(kv)
        try:
            vb = bytes.fromhex(val)
        except ValueError:
            sys.exit(f"[err] --set value not valid hex: {val!r}")
        edits.append((np_, prop, vb, f"0x{val}"))
    for kv in args.u32:
        np_, prop, val = _parse_kv(kv)
        n = int(val, 0)
        edits.append((np_, prop, struct.pack("<I", n & 0xFFFFFFFF), f"u32 {n}"))

    # default action
    if not edits:
        edits = [
            ("/chosen", "sepfw-load-at-boot",    struct.pack("<I", 0), "u32 0"),
            ("/chosen", "protected-data-access", struct.pack("<I", 0), "u32 0"),
        ]
        print("[*] no --set/--u32 given; applying defaults "
              "(/chosen sepfw-load-at-boot=0, protected-data-access=0)")

    print("\n=== EDITS ===")
    any_len_change = False
    for np_, prop, vb, human in edits:
        p = dt.find_prop(np_, prop)
        if p is None:
            sys.exit(f"[err] property not found: {AppleDeviceTree._norm(np_)}/{prop}")
        before = p.value.hex()
        if len(vb) != p.length:
            any_len_change = True
        print(f"  {AppleDeviceTree._norm(np_)}/{prop}")
        print(f"      before: {before} (len {p.length})")
        print(f"      after : {vb.hex()} (len {len(vb)})  <- {human}")
        dt.set_prop(np_, prop, vb)

    if any_len_change:
        print("[!] a value length changed -> tree is re-serialized (offsets shift); "
              "this is fine for booting but the output is not a byte-in-place patch.")

    out_bytes = dt.serialize()

    if args.dry_run:
        print("\n[dry-run] not writing output.")
        return 0

    out_path = args.output or (args.input + ".patched")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(out_bytes)
    print(f"\n[+] wrote {out_path} ({len(out_bytes)} bytes)")

    # verify the written file
    if not args.no_verify:
        dt2 = AppleDeviceTree.parse(open(out_path, "rb").read())
        ok = True
        for np_, prop, vb, _ in edits:
            p2 = dt2.find_prop(np_, prop)
            got = p2.value if p2 else None
            good = got == vb
            ok = ok and good
            mark = "OK" if good else "FAIL"
            print(f"    verify {AppleDeviceTree._norm(np_)}/{prop}: "
                  f"{got.hex() if got is not None else 'MISSING'} [{mark}]")
        # report how many bytes changed vs original (0 structural drift expected
        # when no length changed)
        if len(out_bytes) == len(data):
            diff = sum(1 for a, b in zip(data, out_bytes) if a != b)
            print(f"    byte delta vs original: {diff} bytes changed, size unchanged")
        else:
            print(f"    size changed: {len(data):#x} -> {len(out_bytes):#x} "
                  f"(length-changing edit)")
        if not ok:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())