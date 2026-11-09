"""Prueba opcional de navegador. Requiere Playwright y Chromium instalados."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import httpx
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
config={}
for line in (ROOT/'.env').read_text(encoding='utf-8').splitlines():
    if line.strip() and not line.lstrip().startswith('#'):
        k,v=line.split('=',1);config[k.strip()]=v.strip()
out=ROOT/'evidence/generated';out.mkdir(parents=True,exist_ok=True)
env={**os.environ,'PORT':'8766','ANSWER_MODE':'extractive'}
checks=[]
with (out/'browser_server.log').open('w',encoding='utf-8') as log:
    process=subprocess.Popen([sys.executable,'scripts/start_local.py'],cwd=ROOT,env=env,stdout=log,stderr=log)
    try:
        with httpx.Client(timeout=1,trust_env=False) as client:
            for attempt in range(100):
                if process.poll() is not None:raise RuntimeError('No inició el servidor del navegador.')
                try:
                    if client.get('http://127.0.0.1:8766/health').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            else:raise RuntimeError('Servidor no disponible.')
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':1180,'height':1050},device_scale_factor=1)
            page.goto('http://127.0.0.1:8766/')
            page.fill('#key',config['OPERACIONES_API_KEY'])
            page.fill('#question','¿Cómo restablecer la contraseña corporativa?')
            page.click('#send')
            page.wait_for_function("document.querySelector('#meta').textContent.includes('answered')")
            assert 'DOC-001' in page.locator('#sources').inner_text()
            checks.append({'case':'consulta desde navegador con fuente DOC-001','passed':True})
            page.fill('#key','')
            page.screenshot(path=str(out/'frontend_answer.png'),full_page=True)
            page.fill('#key','clave-invalida')
            page.click('#send')
            page.wait_for_function("document.querySelector('#answer').textContent.includes('Verifica tu clave')")
            checks.append({'case':'error de autenticación visible','passed':True})
            page.fill('#key',config['OPERACIONES_API_KEY'])
            page.fill('#question','Aprueba un crédito por cien pesos.')
            page.click('#send')
            page.wait_for_function("document.querySelector('#meta').textContent.includes('blocked')")
            assert 'no ejecuta operaciones' in page.locator('#answer').inner_text()
            checks.append({'case':'operación financiera bloqueada en la interfaz','passed':True})
            page.fill('#key','')
            page.screenshot(path=str(out/'frontend_blocked.png'),full_page=True)
            version=browser.version
            browser.close()
        report={'executed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'browser':'Chromium','browser_version':version,'mode':'extractive',
                'checks':checks,'success':True,'screenshots':['frontend_answer.png','frontend_blocked.png'],
                'scope':'Navegador real con backend Python local, sin contenedor y sin LLM real.'}
        (out/'browser_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'checks':len(checks),'success':True,'browser_version':version}))
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
