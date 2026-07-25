#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dt_patch2.py — toggle presence-flag properties in an Apple flattened
DeviceTree (iBoot DTB). Handles BOTH:

  * /defaults/content-protect       (restored_external DataEncryptionType)
  * /defaults/no-effaceable-storage (keybagd sub_100003E44 keybag-file path)

Both are ZERO-LENGTH flag properties: only their PRESENCE matters, not any
value. Confirmed from the binaries:

  content-protect      -> present = content protection ON (enum 2, encrypted)
                          absent  = "content-protect property not found" (unencrypted)

  no-effaceable-storage-> keybagd's DT lookup (sub_10001C148) does
                          IORegistryEntryCreateCFProperty("IODeviceTree:/defaults",
                          "no-effaceable-storage") and returns 1 iff the property
                          EXISTS (value is never inspected). sub_100003E44 then:
                              present (w0!=0) -> SKIP loading systembag.kb file
                              absent  (w0==0) -> load the keybag file
                          So ADDING it makes keybagd take the no-effaceable path.

So "changing" these means ADDING or REMOVING the property (presence), not
setting a value. The whole tree is re-serialized losslessly and verified.

Apple DT binary layout (little-endian):
    Node:      uint32 nProperties; uint32 nChildren; Property*; Node*   (recursive)
    Property:  char name[32]; uint32 length (bit31 = placeholder flag);
               uint8 value[length]  (padded to a 4-byte boundary)
    (a node's own name is a property literally called "name")

Usage:
    # content-protect (default target) — remove to disable encryption
    python3 dt_patch2.py DeviceTree.raw --remove -o DeviceTree.patched.raw

    # no-effaceable-storage — ADD to satisfy keybagd's condition
    python3 dt_patch2.py DeviceTree.raw --prop no-effaceable-storage --add -o out.raw
    python3 dt_patch2.py DeviceTree.raw --no-effaceable                -o out.raw   # shortcut

    # do BOTH in one pass (remove content-protect + add no-effaceable-storage)
    python3 dt_patch2.py DeviceTree.raw --unencrypted-keybag-boot -o out.raw

    # generic
    python3 dt_patch2.py DeviceTree.raw --prop <name> --add|--remove [--node /defaults]
    python3 dt_patch2.py DeviceTree.raw --list
    python3 dt_patch2.py DeviceTree.raw --dry-run --prop no-effaceable-storage --add
"""

import sys
import os
import struct
import argparse

FLAG_PLACEHOLDER = 0x80000000
NAME_LEN = 32

# Known presence-flags: name -> (canonical node, recommended default op)
KNOWN_FLAGS = {
    "content-protect":       ("/defaults", "remove"),  # remove => disable encryption
    "no-effaceable-storage": ("/defaults", "add"),     # add    => no-effaceable keybag path
}
DEFAULT_PROP = "content-protect"

CRYPTO_PROPS = {
    "content-protect", "no-effaceable-storage", "cpx-encryption-mode",
    "protected-data-access", "sepfw-load-at-boot", "disable-av-content-protection",
}


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
        # accept ":/defaults", "/defaults", "device-tree/defaults", "IODeviceTree:/defaults"
        p = path.strip()
        for pref in ("IODeviceTree:", "IODeviceTree"):
            if p.startswith(pref):
                p = p[len(pref):]
        p = "/" + p.strip(":").strip("/")
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


# ------------------------------------------------------------------ operations

def apply_flag(dt: "AppleDeviceTree", prop_name: str, op: str, node_path: str):
    """op in {'add','remove'}. Returns (changed: bool, message: str)."""
    found = dt.find_prop_anywhere(prop_name)
    if op == "add":
        if found:
            return False, f"[=] {prop_name} already present at {found[0]} — nothing to do"
        prop = Prop.make(prop_name, value=b"", flags=0)   # zero-length flag
        if not dt.add_prop(node_path, prop):
            raise SystemExit(f"[err] node not found: {AppleDeviceTree._norm(node_path)}")
        return True, f"[+] added {prop_name} (zero-length) to {AppleDeviceTree._norm(node_path)}"
    elif op == "remove":
        if not found:
            return False, f"[=] {prop_name} not present — nothing to do"
        path, node, prop = found
        if prop.length != 0:
            sys.stderr.write(
                f"[warn] {prop_name} is {prop.length} bytes (expected zero-length flag); "
                f"removing anyway\n")
        dt.remove_prop(node, prop_name)
        return True, (f"[-] removed {prop_name} from {path} "
                      f"(was len={prop.length}, node now has {len(node.props)} props)")
    else:
        raise ValueError(op)


# ------------------------------------------------------------------ CLI

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Toggle presence-flags (content-protect / no-effaceable-storage) "
                    "in an Apple DeviceTree (iBoot DTB).")
    ap.add_argument("input", help="DeviceTree.raw (unwrapped IM4P payload)")
    ap.add_argument("-o", "--output", help="output path (default: <input>.patched)")
    ap.add_argument("--prop", default=None,
                    help=f"flag property to operate on (default: {DEFAULT_PROP})")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--add", action="store_true", help="ADD the flag (zero-length)")
    grp.add_argument("--remove", action="store_true", help="REMOVE the flag")
    ap.add_argument("--enable", action="store_true",
                    help="alias for --add (kept for backward compat)")
    ap.add_argument("--node", default=None,
                    help="node to add to (default: canonical node for the property, else /defaults)")
    # convenience combos
    ap.add_argument("--no-effaceable", action="store_true",
                    help="shortcut: ADD /defaults/no-effaceable-storage")
    ap.add_argument("--unencrypted-keybag-boot", action="store_true",
                    help="do BOTH: remove content-protect AND add no-effaceable-storage")
    ap.add_argument("--list", action="store_true",
                    help="print crypto-related properties and exit")
    ap.add_argument("--dry-run", action="store_true", help="show change, do not write")
    ap.add_argument("--no-verify", action="store_true", help="skip round-trip verification")
    args = ap.parse_args(argv)

    data = open(args.input, "rb").read()
    dt = AppleDeviceTree.parse(data)

    if not args.no_verify and dt.serialize() != data:
        sys.stderr.write("[warn] lossless round-trip mismatch before edits — format quirk\n")

    if args.list:
        print("crypto-related properties in tree:")
        any_found = False
        for path, node in dt._walk():
            for p in node.props:
                if p.name in CRYPTO_PROPS:
                    any_found = True
                    u32 = int.from_bytes(p.value, "little") if p.length == 4 else None
                    extra = (f" u32={u32}" if u32 is not None
                             else " (zero-length flag)" if p.length == 0 else "")
                    print(f"  {path}/{p.name:24s} len={p.length}{extra}")
        # also report the ones that are ABSENT (useful to see what to add)
        present = {p.name for _, n in dt._walk() for p in n.props}
        for nm in sorted(CRYPTO_PROPS):
            if nm not in present:
                print(f"  (absent) {nm}")
        if not any_found:
            print("  (none of the known crypto flags are present)")
        return 0

    # Build the list of (prop, op, node) operations to apply.
    ops = []
    if args.unencrypted_keybag_boot:
        ops.append(("content-protect", "remove", "/defaults"))
        ops.append(("no-effaceable-storage", "add", "/defaults"))
    elif args.no_effaceable:
        ops.append(("no-effaceable-storage", "add", "/defaults"))
    else:
        prop = args.prop or DEFAULT_PROP
        canon_node, default_op = KNOWN_FLAGS.get(prop, ("/defaults", "remove"))
        node = args.node or canon_node
        if args.add or args.enable:
            op = "add"
        elif args.remove:
            op = "remove"
        else:
            op = default_op  # sensible default per property
            sys.stderr.write(f"[info] no --add/--remove given; using default op '{op}' for {prop}\n")
        ops.append((prop, op, node))

    changed_any = False
    for prop, op, node in ops:
        changed, msg = apply_flag(dt, prop, op, node)
        changed_any = changed_any or changed
        print(msg)

    out_bytes = dt.serialize()

    if args.dry_run:
        print(f"\n[dry-run] not writing. new size = {len(out_bytes)} (was {len(data)}, "
              f"delta {len(out_bytes) - len(data):+d})")
        return 0

    out_path = args.output or (args.input + ".patched")
    d = os.path.dirname(os.path.abspath(out_path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(out_bytes)
    print(f"\n[+] wrote {out_path} ({len(out_bytes)} bytes, was {len(data)}, "
          f"delta {len(out_bytes) - len(data):+d})")

    if not args.no_verify:
        dt2 = AppleDeviceTree.parse(out_bytes)
        allok = True
        for prop, op, node in ops:
            still = dt2.find_prop_anywhere(prop)
            if op == "add":
                ok = still is not None
                where = f" @ {still[0]}" if still else ""
                print(f"    verify: {prop} present = {ok}{where}  [{'OK' if ok else 'FAIL'}]")
            else:
                ok = still is None
                print(f"    verify: {prop} absent = {ok}  [{'OK' if ok else 'FAIL'}]")
            allok = allok and ok
        # each zero-length flag add/remove shifts the file by exactly 36 bytes
        print(f"    size delta: {len(out_bytes) - len(data):+d} bytes "
              f"(expect +36 per add, -36 per remove of a zero-length flag)")
        if not allok:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())