"""Inicia Uvicorn y prueba HTTP en el mismo entorno; siempre detiene el servidor."""
import os
from pathlib import Path
import subprocess
import sys
import time
import httpx
ROOT=Path(__file__).resolve().parents[1]
if not (ROOT/'.env').exists():
    raise SystemExit('Ejecuta primero python scripts/configure.py.')
env=os.environ.copy()
env['PORT']='8765'
# Esta comprobación valida explícitamente la modalidad extractiva.
env['ANSWER_MODE']='extractive'
out=ROOT/'evidence/generated';out.mkdir(parents=True,exist_ok=True)
with (out/'local_server.log').open('w',encoding='utf-8') as log:
    process=subprocess.Popen([sys.executable,'scripts/start_local.py'],cwd=ROOT,env=env,stdout=log,stderr=log)
    try:
        with httpx.Client(timeout=1,trust_env=False) as client:
            for attempt in range(100):
                if process.poll() is not None:
                    raise RuntimeError('El servidor terminó antes de estar disponible. Revisa local_server.log.')
                try:
                    if client.get('http://127.0.0.1:8765/health').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(0.1)
            else:raise RuntimeError('El servidor no quedó disponible a tiempo.')
        subprocess.run([sys.executable,'scripts/smoke_http.py','--base-url','http://127.0.0.1:8765',
                        '--output','network_smoke.json'],cwd=ROOT,env=env,check=True)
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
