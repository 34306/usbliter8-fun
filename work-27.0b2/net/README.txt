Network-over-USB (reverse tethering) — xem INSTRUCTIONS.md §13b.
- netup.c    : set primary IPv4 service + DNS trong SCDynamicStore (build cho iOS, ký ad-hoc KHÔNG get-task-allow).
- proxyset.c : (apt-only path) set global HTTP proxy.
- uproxy.py  : (apt-only path) HTTP/CONNECT proxy chạy trên Mac.
Build tool iOS: xcrun -sdk iphoneos clang -arch arm64 -framework SystemConfiguration -framework CoreFoundation netup.c -o netup
Ký: ldid -S<ent-có-SCDynamicStore-write+platform-application,KHÔNG-get-task-allow> -Cadhoc netup
