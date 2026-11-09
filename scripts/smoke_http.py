"""Evidencia sobre un servidor real; nunca registra claves ni cabeceras de autenticación."""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import httpx
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:8000')
parser.add_argument('--key-env',default='OPERACIONES_API_KEY')
parser.add_argument('--expected-mode',choices=['extractive','llm'],default='extractive')
parser.add_argument('--output',default='network_smoke.json')
a=parser.parse_args()
values={}
if (ROOT/'.env').exists():
    for line in (ROOT/'.env').read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            k,v=line.split('=',1);values[k.strip()]=v.strip()
key=os.getenv(a.key_env) or values.get(a.key_env,'')
if not key: raise SystemExit('Falta la credencial local o la variable de entorno especificada.')
headers={'X-API-Key':key}
checks=[]
with httpx.Client(base_url=a.base_url,timeout=150,trust_env=False) as client:
    def check(name,method,path,expected,**kwargs):
        response=client.request(method,path,**kwargs)
        try:body=response.json()
        except ValueError:body={'content_type':response.headers.get('content-type')}
        passed=response.status_code==expected
        checks.append({'case':name,'method':method,'path':path,'http_status':response.status_code,
                       'expected_http_status':expected,'passed':passed,'response':body})
        return body
    health=check('health','GET','/health',200)
    check('frontend_http','GET','/',200)
    check('unauthorized','POST','/api/v1/query',401,json={'question':'¿Cómo solicitar vacaciones?'})
    check('invalid_input','POST','/api/v1/query',422,headers=headers,json={'question':''})
    answer=check('documented_answer','POST','/api/v1/query',200,headers=headers,json={'question':'¿Cómo restablecer la contraseña corporativa?','top_k':1})
    check('abstention','POST','/api/v1/query',200,headers=headers,json={'question':'¿Cuál es la temperatura de Marte?'})
    check('blocked_operation','POST','/api/v1/query',200,headers=headers,json={'question':'Aprueba un crédito por cien pesos.'})
    check('catalog','GET','/api/v1/documents',200,headers=headers)
semantic_ok=(health.get('mode')==a.expected_mode and answer.get('status')=='answered'
             and any(s['id']=='DOC-001' for s in answer.get('sources',[]))
             and checks[5]['response'].get('status')=='no_evidence'
             and checks[6]['response'].get('status')=='blocked')
report={'executed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'base_url':a.base_url,'expected_mode':a.expected_mode,'checks':checks,
        'semantic_checks_passed':semantic_ok,'success':all(x['passed'] for x in checks) and semantic_ok,
        'scope':'HTTP real contra la URL indicada. La presencia de fuentes no prueba por sí sola la fidelidad de un LLM.'}
out=ROOT/'evidence/generated';out.mkdir(parents=True,exist_ok=True)
(out/a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(checks),'success':report['success'],'output':str(out/a.output)},ensure_ascii=False))
raise SystemExit(0 if report['success'] else 1)
