#!/usr/bin/env python3
# usbliter8 CFW — skip Setup by disabling the ScreenTime/FamilyControls launchd jobs.
#
# Usage:
#   ./disable_screentime.py <disabled.plist>        # patch in place
#   ./disable_screentime.py --show <disabled.plist> # just print current state
#
# Why: after hacktivation, Setup still hangs on the loading spinner. Crash log
# (Setup-*.ips): "scene-update watchdog transgression: com.apple.purplebuddy
# exhausted 10s". The stackshot shows Setup blocked on com.apple.ScreenTimeAgent
# (it accepts the XPC connection but never replies) -> watchdog kills Setup -> loop.
#
# ScreenTimeAgent is an ON-DEMAND job (MachServices, has `.setup`), so renaming its
# LaunchDaemon plist does NOTHING — launchd on-demand-launches it from the cache.
# The working fix is to let launchd REFUSE the launch, via its disabled overrides:
# then Setup's XPC fails fast instead of hanging, and it walks through to Home.
#
# Device path:  /var/db/com.apple.xpc.launchd/disabled.plist
# From SSHRD:   /mnt2/db/com.apple.xpc.launchd/disabled.plist   (Data volume)
#
# Pull it to the Mac, run this, push it back, reboot:
#   scp root@10.7.0.2:/var/db/com.apple.xpc.launchd/disabled.plist .
#   ./disable_screentime.py disabled.plist
#   scp disabled.plist root@10.7.0.2:/var/db/com.apple.xpc.launchd/disabled.plist
#
# Written back as a BINARY plist (launchd will not read an XML one here).

import sys, os, plistlib

LABELS = [
    "com.apple.ScreenTimeAgent",          # the one Setup actually blocks on
    "com.apple.ScreenTimeSettingsAgent",
    "com.apple.FamilyControlsAgent",
    "com.apple.familycircled",
    "com.apple.familynotificationd",
]


def load(path):
    with open(path, "rb") as f:
        d = plistlib.load(f)
    if not isinstance(d, dict):
        sys.exit(f"!! {path}: expected a dict at the root, got {type(d).__name__}")
    return d


def main():
    argv = sys.argv[1:]
    show = argv[:1] == ["--show"]
    if show:
        argv = argv[1:]
    if len(argv) != 1:
        print(f"usage: {sys.argv[0]} [--show] <disabled.plist>")
        sys.exit(1)
    path = argv[0]

    if os.path.exists(path):
        d = load(path)
    elif show:
        sys.exit(f"!! {path}: not found")
    else:
        # launchd is fine with us creating it; a missing file just means nothing
        # has ever been disabled on this device.
        print(f"[!] {path} not found — creating a new one")
        d = {}

    if show:
        for label in LABELS:
            print(f"  {label:38s} {d.get(label, '<absent>')}")
        return

    changed = []
    for label in LABELS:
        old = d.get(label, "<absent>")
        if old is not True:
            d[label] = True
            changed.append(label)
        print(f"  {label:38s} {old} -> True")

    with open(path, "wb") as f:
        plistlib.dump(d, f, fmt=plistlib.FMT_BINARY)

    # verify by re-reading what we just wrote
    d2 = load(path)
    bad = [l for l in LABELS if d2.get(l) is not True]
    if bad:
        sys.exit(f"[FAIL] not disabled after write: {', '.join(bad)}")
    print(f"[OK] {len(LABELS)} labels disabled ({len(changed)} changed), "
          f"{len(d2)} entries total. Now: push back to the device and reboot.")


if __name__ == "__main__":
    main()
