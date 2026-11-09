"""Construye y comprueba la imagen con un daemon Docker real; sin simular evidencia.
Precondición: ejecutar configure.py y docker compose up -d --build --wait.
"""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
if not shutil.which('docker'):
    raise SystemExit('Docker no está disponible. No se generó evidencia de contenedor.')
out=ROOT/'evidence/generated';out.mkdir(parents=True,exist_ok=True)
def run(args):
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    if p.returncode:
        raise SystemExit('Falló '+ ' '.join(args)+'\n'+p.stderr)
    return p.stdout.strip()
run(['docker','info','--format','{{.ServerVersion}}'])
image=json.loads(run(['docker','image','inspect','copiloto-horizonte:1.0.0',
                     '--format','{{json .Id}}']))
cid=run(['docker','compose','ps','-q','api'])
if not cid: raise SystemExit('No hay contenedor api en ejecución.')
actual_image=run(['docker','inspect','--format','{{.Image}}',cid])
if actual_image!=image: raise SystemExit('El contenedor no corresponde a la imagen etiquetada verificada.')
# No se hace un inspect completo: contendría variables de entorno y secretos.
state=json.loads(run(['docker','inspect','--format','{{json .State}}',cid]))
user=run(['docker','inspect','--format','{{.Config.User}}',cid])
if not state.get('Running') or state.get('Health',{}).get('Status')!='healthy':
    raise SystemExit('El contenedor no está ejecutándose con salud healthy.')
if user!='appuser': raise SystemExit('El contenedor no utiliza el usuario esperado.')
run([sys.executable,'scripts/smoke_http.py','--output','container_http.json'])
test_log=run(['docker','compose','--profile','test','run','--build','--rm','tests'])
(out/'container_tests.txt').write_text(test_log,encoding='utf-8')
report={'executed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'image_id':image,'container_id':cid,'running':state['Running'],
        'health':state['Health']['Status'],'user':user,'container_tests_exit_code':0,
        'network_report':'container_http.json','success':True}
(out/'docker_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
