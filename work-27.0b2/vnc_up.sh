#!/bin/sh
# vnc_up.sh — SAU MỖI LẦN NORMAL BOOT: dựng mạng USB + bật TrollVNC + mở Screen Sharing.
# Chạy TRÊN MAC (máy iPhone đã vào iOS + cắm USB):
#   cd work-27.0b2 && ./vnc_up.sh
# Kết nối thủ công (nếu cần): macOS Screen Sharing -> vnc://10.7.0.2:5901  (mật khẩu: alpine)

BASE="$(cd "$(dirname "$0")" && pwd)"
DEV_IP=10.7.0.2
VNC_PORT=5901
VNC_PASS=alpine
SSHPASS="$BASE/../tools/sshpass"
SSHOPT="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o PreferredAuthentications=password -o PubkeyAuthentication=no -o ConnectTimeout=8"

# 1) Mạng USB (Mac NAT + device IP/route/DNS). net_up.sh tự dò iface + retry.
echo "===== [1/3] Mạng USB ====="
sh "$BASE/net_up.sh" || { echo "!! net_up.sh lỗi — dừng."; exit 1; }

# 2) Bật TrollVNC trên device (kill bản cũ, start lại bằng tvncd = posix_spawn App-type + SETSID)
echo "===== [2/3] Bật TrollVNC ====="
"$SSHPASS" -p alpine ssh $SSHOPT root@$DEV_IP 'export PATH=/var/jb/usr/bin:/var/jb/bin:/usr/bin:/bin:/usr/sbin:/sbin
for p in $(/bin/ps ax | grep "[t]rollvncserver" | awk "{print \$1}"); do kill -9 $p 2>/dev/null; done
sleep 1
/var/jb/usr/bin/tvncd
sleep 3
if /usr/sbin/netstat -an | grep "\.'"$VNC_PORT"' " | grep -q LISTEN; then echo "VNC server LISTEN :'"$VNC_PORT"'"; else echo "VNC FAIL — xem /tmp/tvnc.log:"; tail -6 /tmp/tvnc.log; fi'

# 3) Mở macOS Screen Sharing
echo "===== [3/3] Mở Screen Sharing ====="
if nc -z -w 4 "$DEV_IP" "$VNC_PORT" 2>/dev/null; then
  open "vnc://:$VNC_PASS@$DEV_IP:$VNC_PORT"
  echo "[✓] Đã mở vnc://$DEV_IP:$VNC_PORT (pass=$VNC_PASS). Xem/điều khiển màn hình iPhone."
else
  echo "!! Port $VNC_PORT chưa mở từ Mac. Thử chạy lại, hoặc ssh root@$DEV_IP chạy /var/jb/usr/bin/tvncd."
fi
