#!/usr/bin/env python3
# usbliter8 CFW — userland byte-patches for iOS 27.0b2 (24A5370h) / iPhone12,3
#
# Usage:
#   ./userland_patches.py coreauthd        <coreauthd_binary>
#   ./userland_patches.py ctkd             <ctkd_binary>
#   ./userland_patches.py mobileactivationd <mobileactivationd_binary>
#
# Patches in place (make a .orig backup yourself first). AFTER patching, re-sign
# ad-hoc PRESERVING entitlements, e.g.:
#   ldid -e file.orig > ents.plist
#   ldid -S ents.plist -Cadhoc file
# then deploy to the device System volume (live-fs, snapshot must be renamed) and sync.
#
# ⚠️ Offsets are build-specific (24A5370h). Re-verify for other builds in IDA.
#
# NOTE: skipping Setup (the ScreenTimeAgent deadlock) is NOT a byte patch — it is a
# launchd override. See ./disable_screentime.py.

import sys, struct

NOP      = 0xD503201F
MOVX0_0  = 0xD2800000   # mov x0, #0
MOVW0_1  = 0x52800020   # mov w0, #1
RET      = 0xD65F03C0   # ret
ADRP_X0  = 0x90000620   # adrp x0, ...      (page of CFString "Activated")
ADD_X0_8 = 0x91002000   # add  x0, x0, #8

# name -> list of (file_offset, u32_value, comment)
PATCHES = {
    # -[TKSEPKeyServer serverAttributesOfKey:error:] -> return nil
    # (avoids uncaught NSException from -[TKLocalSEPRefKey keyType] on fake SEP)
    "ctkd": [
        (0x1B38, MOVX0_0, "mov x0,#0  (serverAttributesOfKey:error: -> nil)"),
        (0x1B3C, RET,     "ret"),
    ],
    # coreauthd: NOP the `BL _objc_msgSend$startController` in the DTO pending-policy
    # startup block -> skips SEP DTO-ratchet parse that null-derefs (0x120).
    "coreauthd": [
        (0x95C0, NOP, "NOP BL startController"),
    ],
    # mobileactivationd: offline hacktivation.
    "mobileactivationd": [
        # -[DeviceType should_hactivate] -> 1  (the `ret` right after is kept)
        # logs: "Hactivation is enabled, short circuiting activation state to Activated"
        (0x2EBB14, MOVW0_1,  "mov w0,#1  (should_hactivate -> YES)"),
        # getActivationStateWithCompletionBlock -> CFString "Activated"
        (0x327CB0, NOP,      "NOP"),
        (0x327D10, ADRP_X0,  "adrp x0, <page of \"Activated\">"),
        (0x327D14, ADD_X0_8, "add  x0, x0, #8"),
        (0x327D18, NOP,      "NOP"),
    ],
}

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in PATCHES:
        print(f"usage: {sys.argv[0]} <{'|'.join(PATCHES)}> <binary>")
        sys.exit(1)
    name, path = sys.argv[1], sys.argv[2]
    d = bytearray(open(path, "rb").read())
    for off, val, cmt in PATCHES[name]:
        old = struct.unpack_from("<I", d, off)[0]
        struct.pack_into("<I", d, off, val)
        print(f"  {name} @ {off:#x}: {old:08x} -> {val:08x}   # {cmt}")
    open(path, "wb").write(d)
    # verify
    d2 = open(path, "rb").read()
    ok = all(struct.unpack_from("<I", d2, off)[0] == val for off, val, _ in PATCHES[name])
    print(f"[{'OK' if ok else 'FAIL'}] patched {name} ({len(PATCHES[name])} words). Now: re-sign ad-hoc WITH entitlements, deploy, sync.")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
