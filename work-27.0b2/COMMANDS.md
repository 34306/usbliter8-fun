# COMMANDS — cheatsheet (tránh nhầm chain)

Thư mục chạy: `work-27.0b2/`. Máy checkm8 **tethered** → mỗi lần boot phải **pwndfu** trước.
Askpass (hỏi mật khẩu qua hộp thoại, không lưu mật khẩu vào file/repo):
```sh
cat > /tmp/ap.sh <<'EOF'
#!/bin/sh
/usr/bin/osascript -e 'display dialog "sudo password:" default answer "" with hidden answer' -e 'text returned of result'
EOF
chmod +x /tmp/ap.sh
```

> ⚠️ **NGUYÊN TẮC VÀNG**: `Ramdisk/` chứa chain của LẦN build gần nhất.
> - Muốn **normal boot** → phải chạy `get_boot.py` NGAY TRƯỚC `boot.py`.
> - Muốn **SSHRD** → phải `cp -r Ramdisk_SSH_bak Ramdisk` NGAY TRƯỚC `boot_rd.sh`.
> Quên bước rebuild = boot nhầm chain (vd đang muốn normal lại ra SSHRD).

---

## 1) NORMAL BOOT (vào iOS thật)
```sh
# [máy đang pwndfu]
python3 -c "import usb.core;print('pwndfu' if usb.core.find(idProduct=0x1227) else 'NO DFU')"
SUDO_ASKPASS=/tmp/ap.sh ./get_boot.py          # BẮT BUỘC: dựng lại normal chain (ephemeral + apticket + kernel patch)
ls Ramdisk/ | grep -c RestoreRamdisk           # phải = 0 (0 = normal chain; >0 = còn SSHRD chain, SAI)
./boot.py                                       # gửi → boot vào Home
```

## 2) SSHRD (ramdisk, để vá/mount/sửa fs)
```sh
# [máy đang pwndfu]
rm -rf Ramdisk && cp -r Ramdisk_SSH_bak Ramdisk   # BẮT BUỘC: nạp SSHRD chain
ls Ramdisk/ | grep -c RestoreRamdisk               # phải = 1 (có RestoreRamdisk = SSHRD)
./boot_rd.sh                                        # boot SSH ramdisk
```

## 3) SSH + iproxy (dùng cho CẢ normal boot lẫn SSHRD, port 22 → 2222)
```sh
pkill -f "iproxy 2222"; iproxy 2222 22 &
# password: alpine
../tools/sshpass -p alpine ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o PreferredAuthentications=password -o PubkeyAuthentication=no -p 2222 root@localhost
```
Phân biệt đang ở đâu (chạy trong SSH):
```sh
/sbin/mount | grep -q 'md0 on /' && echo "SSHRD (ramdisk)" || echo "NORMAL boot"
# SSHRD: / = /dev/md0 (ro); System=/mnt1 ; Data=/mnt2 ; Preboot=disk1s6
# NORMAL: / = disk1s1 (System, RO khi boot) ; /var = Data (rw)
```

## 4) SSHRD — mount volumes
```sh
/sbin/mount_apfs /dev/disk1s1 /mnt1 ; /sbin/mount -u -o rw /dev/disk1s1   # System rw (rootful)
/sbin/mount_apfs /dev/disk1s2 /mnt2 ; /sbin/mount -u -o rw /dev/disk1s2   # Data rw
# công cụ thiếu trên ramdisk (mkdir/mv/tar/ln...) → dùng bundle của Filza:
#   /mnt1/Applications/Filza.app/bins/bin/{mkdir,mv,cp,rm,ln,tar}
```

## 5) Trên NORMAL boot (qua SSH) — thao tác app / bootstrap
```sh
export PATH=/var/jb/usr/bin:/var/jb/bin:/var/jb/usr/sbin:/var/jb/sbin:/usr/bin:/bin:/usr/sbin:/sbin
# đăng ký app (sau khi drop .app vào /Applications qua SSHRD):
cd /Applications/TrollStoreLite.app && ./trollstorehelper refresh-all
# respring:
/bin/ps ax | while read pid rest; do case "$rest" in *CoreServices/SpringBoard.app/SpringBoard) /bin/kill -9 "$pid";; esac; done
# bootstrap (chỉ chạy 1 lần, sau khi extract /var/jb):
/var/jb/prep_bootstrap.sh
/var/jb/usr/bin/dpkg -i /var/jb/sileo.deb
```

## 6) apticket — dump lại SAU MỖI restore (bắt buộc, xem INSTRUCTIONS §4)
```sh
# [SSHRD] Preboot=disk1s6
/sbin/mount_apfs -o rdonly /dev/disk1s6 /mnt6
find /mnt6 -name sep-firmware.img4   # pull về Mac → img4tool -e -m t8030_apticket.der dev_sep.img4
```

## 7) Restore sạch (erase + flash)
```sh
SUDO_ASKPASS=/tmp/ap.sh ./make_cfw.py            # dựng CFW + restore chain (iBSS = -restore)
python3 tss_proxy_server.py &                     # TSS proxy local (beta unsigned)
./restore_cfw.sh                                  # idevicerestore -e -y
# panic "enter restore mode" → COLD RESET máy rồi thử lại
```

## 8) MẠNG QUA USB (reverse tethering) — chạy SAU MỖI NORMAL boot
Máy WiFi/USB-activation chết → chia internet từ Mac qua USB-ethernet. **1 lệnh:**
```sh
# [máy đã NORMAL boot + cắm USB]  — chạy trên Mac
cd work-27.0b2 && ./net_up.sh          # tự dò iface, set Mac+device, in HTTP 200 nếu OK
```
Script tự làm: Mac `en31=10.7.0.1` + `ip.forwarding=1` + pf NAT `10.7.0.0/24 -> en0`; device `en2=10.7.0.2` + default route `10.7.0.1` + `/var/jb/netup` (SCDynamicStore primary service + DNS 8.8.8.8/1.1.1.1). Test cuối phải in `200`.

Làm tay (nếu cần), Mac:
```sh
SUDO_ASKPASS=/tmp/ap.sh sudo -A ifconfig en31 inet 10.7.0.1 netmask 255.255.255.0
SUDO_ASKPASS=/tmp/ap.sh sudo -A sysctl -w net.inet.ip.forwarding=1
printf 'nat on en0 from 10.7.0.0/24 to any -> (en0)\npass all\n' > /tmp/usbnat.pf
SUDO_ASKPASS=/tmp/ap.sh sudo -A pfctl -ef /tmp/usbnat.pf   # en0=iface internet của Mac (route -n get default)
```
Device (qua SSH):
```sh
/sbin/ifconfig en2 inet 10.7.0.2 netmask 255.255.255.0
/sbin/route -n delete default 2>/dev/null; /sbin/route -n add default 10.7.0.1
/var/jb/netup                                  # IP tĩnh 10.7.0.2/10.7.0.1 đã baked trong netup
```
⚠️ **KHÔNG** dùng địa chỉ auto `169.254.x.x`: đó là link-local, **random lại mỗi boot** → netup/route sai. Luôn ép IP tĩnh `10.7.0.x` (đã khớp với `netup`).
⚠️ Sau khi có internet trực tiếp, **XOÁ** `/var/jb/etc/apt/apt.conf.d/00proxy.conf` (proxy `127.0.0.1:8888` cũ) nếu còn — nó làm `apt update`/Sileo báo "package unavailable" / connection refused.

## 9) apt / Sileo / neofetch
```sh
apt-get update                                 # phải 'Hit', không 'connect 127.0.0.1:8888'
apt-get install -y neofetch; neofetch          # neofetch đã wrap thành binary (shebang script bị kernel chặn)
# Sileo báo "package unavailable" -> xoá 00proxy.conf (§8), kill Sileo, mở lại + kéo refresh
```
⚠️ Package dạng **script** (`#!/usr/bin/env ...`) không chạy thẳng (kernel chặn exec shebang, `/usr/bin/env` không có ở rootless). Chạy tạm: `bash <script>`; hoặc wrap thành binary như `neofetch` (xem `net/shwrap.c` pattern).

## 10) TrollVNC — xem + điều khiển màn hình (qua USB)
**1 lệnh sau mỗi boot** (Mac; máy đã NORMAL + cắm USB): dựng mạng + bật VNC + mở viewer:
```sh
cd work-27.0b2 && ./vnc_up.sh
# -> macOS Screen Sharing mở vnc://10.7.0.2:5901  (mật khẩu: alpine)
# chuột=chạm, kéo=vuốt, chuột phải / 2 ngón = Home
```
Bật tay (nếu chỉ cần server, đã có mạng §8):
```sh
../tools/sshpass -p alpine ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@10.7.0.2 /var/jb/usr/bin/tvncd
open "vnc://:alpine@10.7.0.2:5901"
```
Cài lại (sau restore sạch) — copy 2 file trong `work-27.0b2/vnc/` sang device rồi chạy tvncd:
```sh
S=../tools/sshpass; O="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
$S -p alpine ssh $O root@10.7.0.2 'cat > /var/jb/usr/bin/trollvncserver && chmod +x /var/jb/usr/bin/trollvncserver' < vnc/trollvncserver
$S -p alpine ssh $O root@10.7.0.2 'cat > /var/jb/usr/bin/tvncd && chmod +x /var/jb/usr/bin/tvncd' < vnc/tvncd
```
Chi tiết:
- `vnc/trollvncserver` = binary prebuilt lấy từ vphone-cli-storage (`cfw_input.tar.zst → iosbinpack64/bin/`), đã **re-sign ad-hoc** giữ 243 entitlements (screen-capture QuartzCore + HID input), **bỏ** get-task-allow. Link tĩnh libvncserver/turbojpeg → self-contained.
- `vnc/tvncd` (src `tvncd.c`) = daemonizer: `posix_spawn` với **App process type + SETSID**.
  - ⚠️ Bắt buộc App-type: daemon thường → `IOSurface 0x0` "Failed to get screen dimensions". Chỉ App-type mới có quyền display.
  - SETSID → sống qua khi đóng SSH.
- Kết nối qua **ethernet USB `10.7.0.2`** (không dùng iproxy; usbmux hay reset). Env baked: pass=`alpine`, DISABLE_TWEAKS=1, port `5901`.
- Log server: `/tmp/tvnc.log` trên device.

---
### Lỗi hay gặp
- Boot normal ra SSHRD → quên `get_boot.py` (Ramdisk còn SSHRD chain). Fix: chạy get_boot.py rồi boot.py.
- Màn đen normal boot → apticket stale (chưa dump sau restore) → §6 + INSTRUCTIONS §4.
- `usb.core` báo "iOS-USB" nhưng thực ra SSHRD → SSHRD enumerate giả 0x12a8; xác định bằng `mount | grep md0` (§3).
- App mở đen/crash → binary còn `get-task-allow` (AMFI giết ad-hoc) → re-sign BỎ get-task-allow (INSTRUCTIONS).
- Sau reboot mất mạng USB → IP link-local 169.254 random lại → chạy `./net_up.sh` (ép IP tĩnh 10.7.0.x). apt "connect 127.0.0.1:8888" → xoá `00proxy.conf` (§8).
- SSH `iproxy 2222` (usbmux) reset ở kex nhưng dropbear vẫn sống → SSH thẳng `root@10.7.0.2` qua ethernet (cần net_up.sh trước).
- TrollVNC "Failed to get screen dimensions" / IOSurface 0x0 → chạy sai kiểu process; phải qua `tvncd` (App spawn type), đừng chạy `trollvncserver` trần dạng daemon.
- `launchctl` (/var/jb) abort "Symbol not found _launch_active_user_switch" → launchctl rootless không tương thích build này; đừng dùng bootstrap/bootout, chạy daemon qua `tvncd` hoặc launchd cache.
