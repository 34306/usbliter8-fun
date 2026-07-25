import socket, threading, select, sys
def pipe(a,b):
    try:
        while True:
            r,_,_=select.select([a,b],[],[],60)
            if not r: break
            for s in r:
                d=s.recv(65536)
                if not d: return
                (b if s is a else a).sendall(d)
    except: pass
    finally:
        for s in (a,b):
            try: s.close()
            except: pass
def handle(c):
    try:
        c.settimeout(30)
        data=b""
        while b"\r\n\r\n" not in data:
            ch=c.recv(4096)
            if not ch: c.close(); return
            data+=ch
        head=data.split(b"\r\n\r\n",1)[0]
        line=head.split(b"\r\n")[0]
        method,url,_=line.split(b" ",2)
        if method==b"CONNECT":
            host,port=url.rsplit(b":",1); port=int(port)
            up=socket.create_connection((host.decode(),port),timeout=30)
            c.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        else:
            # plain HTTP: Host header
            host=None
            for h in head.split(b"\r\n")[1:]:
                if h.lower().startswith(b"host:"): host=h.split(b":",1)[1].strip(); break
            if not host: c.close(); return
            hp=host.split(b":"); hh=hp[0].decode(); pp=int(hp[1]) if len(hp)>1 else 80
            up=socket.create_connection((hh,pp),timeout=30)
            up.sendall(data)
        c.settimeout(None); up.settimeout(None)
        pipe(c,up)
    except Exception as e:
        try: c.close()
        except: pass
def main():
    srv=socket.socket(); srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    srv.bind(("127.0.0.1",8888)); srv.listen(64)
    print("proxy on 127.0.0.1:8888")
    while True:
        c,_=srv.accept(); threading.Thread(target=handle,args=(c,),daemon=True).start()
main()
