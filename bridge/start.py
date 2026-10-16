#!/usr/bin/env python3
"""Start the installed local app and reuse healthy existing services."""
import json, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT.parent/'crime-stoppers'
LOGS=CASE/'data'/'osintcase'
LOGS.mkdir(parents=True,exist_ok=True)
def ready(url):
    try:
        with urllib.request.urlopen(url,timeout=2) as r:return isinstance(json.load(r),dict)
    except Exception:return False

def start(name,command,url):
    if ready(url):return
    with (LOGS/(name+'.log')).open('a') as log:
        process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    for _ in range(40):
        if ready(url):return
        if process.poll() is not None:break
        time.sleep(.25)
    raise SystemExit(f'{name} failed to start. Read {LOGS/(name+".log")}')

if not (ROOT/'dist/index.html').exists():subprocess.run(['npm','run','build'],cwd=ROOT,check=True)
start('backend',[sys.executable,str(CASE/'server.py'),'--port','8765'],'http://127.0.0.1:8765/api/stats')
start('bridge',[sys.executable,str(ROOT/'bridge/server.py')],'http://127.0.0.1:8770/bridge/status')
subprocess.run(['open','http://127.0.0.1:8770'],check=True)
print('Open http://127.0.0.1:8770')
