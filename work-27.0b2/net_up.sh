#!/bin/sh
# net_up.sh — reverse USB tethering: Mac chia internet cho iPhone CFW qua USB-ethernet.
# Chạy TRÊN MAC sau mỗi lần NORMAL boot (máy đã vào iOS + cắm USB).
#   cd work-27.0b2 && ./net_up.sh
# Mặc định: Mac=10.7.0.1  device=10.7.0.2  (khớp IP tĩnh baked trong /var/jb/netup)

BASE="$(cd "$(dirname "$0")" && pwd)"
ASKPASS=/tmp/ap.sh
# Hỏi mật khẩu sudo bằng hộp thoại macOS — KHÔNG hardcode mật khẩu vào repo.
[ -f "$ASKPASS" ] || cat > "$ASKPASS" <<'EOF'
#!/bin/sh
/usr/bin/osascript -e 'display dialog "sudo password:" default answer "" with hidden answer with title "net_up.sh"' -e 'text returned of result'
EOF
chmod +x "$ASKPASS"; export SUDO_ASKPASS="$ASKPASS"

MAC_IP=10.7.0.1; DEV_IP=10.7.0.2; MASK=255.255.255.0; SUBNET=10.7.0.0/24
SSHPASS="$BASE/../tools/sshpass"
SSHOPT="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PreferredAuthentications=password -o PubkeyAuthentication=no -o ConnectTimeout=8"

# 1) Mac internet iface = default route
WAN=$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')
[ -n "$WAN" ] || { echo "!! Mac không có default route (không có internet)"; exit 1; }
echo "[*] WAN (internet) = $WAN"

# 2) dò USB-ethernet iface tới device.
#    Sau reboot máy re-enumerate -> iface Mac đổi tên (en31->en35...) và iface CŨ còn giữ 10.7.0.1 (stale).
#    Ưu tiên iface có link-local 169.254 (device VỪA cắm), rồi mới tới iface đang giữ 10.7.0.1.
#    Đồng thời xoá 10.7.0.1 khỏi các iface khác để khỏi trùng IP / dò nhầm.
USBIF=""; FALLBACK=""
for i in $(ifconfig -l | tr ' ' '\n' | grep '^en'); do
  [ "$i" = "$WAN" ] && continue
  ifconfig "$i" 2>/dev/null | grep -q 'status: active' || continue
  if ifconfig "$i" 2>/dev/null | grep -qE 'inet 169\.254'; then USBIF="$i"; break; fi
  ifconfig "$i" 2>/dev/null | grep -q 'inet 10\.7\.0\.1' && FALLBACK="$i"
done
[ -n "$USBIF" ] || USBIF="$FALLBACK"
[ -n "$USBIF" ] || { echo "!! Không thấy USB-ethernet iface (device đã NORMAL boot + cắm USB chưa?)"; exit 1; }
# gỡ 10.7.0.1 stale khỏi iface khác
for i in $(ifconfig -l | tr ' ' '\n' | grep '^en'); do
  [ "$i" = "$USBIF" ] && continue
  ifconfig "$i" 2>/dev/null | grep -q 'inet 10\.7\.0\.1' && sudo -A ifconfig "$i" inet 0.0.0.0 2>/dev/null
done
echo "[*] USB-eth iface = $USBIF"

# 3) Mac: IP tĩnh + forwarding + pf NAT
sudo -A ifconfig "$USBIF" inet $MAC_IP netmask $MASK
sudo -A sysctl -w net.inet.ip.forwarding=1 >/dev/null
printf 'nat on %s from %s to any -> (%s)\npass all\n' "$WAN" "$SUBNET" "$WAN" > /tmp/usbnat.pf
sudo -A pfctl -ef /tmp/usbnat.pf 2>/dev/null
echo "[*] Mac: $USBIF=$MAC_IP, forwarding=1, NAT $SUBNET -> $WAN"

# 4) SSH tunnel qua usbmux (IP-independent — cần vì lúc mới boot device chưa có 10.7.0.2)
pkill -f "iproxy 2222" 2>/dev/null
( iproxy 2222 22 >/dev/null 2>&1 & ); sleep 1

# 5) Device: IP tĩnh en2 + default route + netup (SCDynamicStore primary + DNS)
#    usbmux đôi lúc reset -> thử qua ethernet (nếu device đã cấu hình) rồi fallback usbmux, retry.
DEV_CMD="export PATH=/var/jb/usr/bin:/var/jb/bin:/usr/bin:/bin:/usr/sbin:/sbin
/sbin/ifconfig en2 inet $DEV_IP netmask $MASK
/sbin/route -n delete default 2>/dev/null
/sbin/route -n add default $MAC_IP >/dev/null
/var/jb/netup"
ok=""
for t in 1 2 3 4; do
  if "$SSHPASS" -p alpine ssh $SSHOPT root@$DEV_IP "$DEV_CMD" 2>/dev/null; then ok=eth; break; fi
  if "$SSHPASS" -p alpine ssh $SSHOPT -p 2222 root@localhost "$DEV_CMD" 2>/dev/null; then ok=usbmux; break; fi
  echo "  [retry $t] SSH tới device chưa được, thử lại..."; pkill -f "iproxy 2222" 2>/dev/null; ( iproxy 2222 22 >/dev/null 2>&1 & ); sleep 2
done
[ -n "$ok" ] || { echo "!! Không SSH được vào device (thử cả ethernet lẫn usbmux). Kiểm tra máy đã NORMAL boot + cắm USB."; exit 1; }
echo "[*] device: en2=$DEV_IP, default via $MAC_IP, netup OK (qua $ok)"

# 6) verify (in mã HTTP; 200 = OK) — qua ethernet 10.7.0.2
printf '[*] test internet trên device (HTTP code apt.procurs.us): '
"$SSHPASS" -p alpine ssh $SSHOPT root@$DEV_IP \
  '/var/jb/usr/bin/curl -s -o /dev/null -w "%{http_code}\n" --max-time 12 https://apt.procurs.us/ 2>&1'
echo "[✓] 200 = mạng USB đã lên (apt/Sileo/Safari dùng được). Khác 200 = xem lại cắm USB / chạy lại."
