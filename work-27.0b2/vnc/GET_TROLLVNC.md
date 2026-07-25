# Lấy `trollvncserver` (binary VNC)

`trollvncserver` là VNC server *standalone daemon* của **[OwnGoalStudio/TrollVNC](https://github.com/OwnGoalStudio/TrollVNC)**
(GPLv2, link tĩnh **LibVNC**). Repo này **không kèm** binary (tránh redistribute binary GPL của bên
thứ 3). Có 2 cách lấy:

## Cách A — dùng bản build sẵn từ vphone-cli-storage (mình đã dùng)
Nguồn: **[Lakr233/vphone-cli](https://github.com/Lakr233/vphone-cli)** (submodule `vphone-cli-storage`).
```sh
git clone --depth 1 https://github.com/Lakr233/vphone-cli-storage.git
cd vphone-cli-storage
# giải nén cfw_input.tar.zst rồi lấy iosbinpack64/bin/trollvncserver
tar --zstd -xf cfw_input.tar.zst cfw_input/jb/iosbinpack64.tar
mkdir ibp && tar -xf cfw_input/jb/iosbinpack64.tar -C ibp
cp ibp/iosbinpack64/bin/trollvncserver .
```

## Cách B — tự build từ source
Fork `OwnGoalStudio/TrollVNC`, chạy GitHub Action "Build TrollVNC", tải artifact. (Repo đã vendor
sẵn libvncserver/turbojpeg/... trong `lib/` + `include/`, theos-based.)

## Sau khi có binary — re-sign ad-hoc (GIỮ entitlements, BỎ get-task-allow)
```sh
ldid -e trollvncserver > trollvncserver.entitlements   # (file này đã kèm sẵn để tham khảo)
ldid -Strollvncserver.entitlements -Cadhoc trollvncserver
# verify: ldid -e trollvncserver | grep -c get-task-allow  -> phải 0
```
Rồi deploy `/var/jb/usr/bin/trollvncserver` và chạy qua `tvncd` (xem BLOG §11 / COMMANDS §10).

> 243 entitlements gồm QuartzCore capture + HID event-dispatch/injection + IOSurface.protected-access.
> Chạy qua `tvncd` (App spawn type) — KHÔNG chạy trực tiếp dạng daemon (sẽ `IOSurface 0x0`).
