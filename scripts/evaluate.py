"""Evaluación de recuperación sobre consultas sintéticas de desarrollo, no prueba externa."""
import datetime
import json
from pathlib import Path
import statistics
import sys
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.config import Settings
from app.main import create_app
settings=Settings('evaluation-operations-key-123456','evaluation-risks-key-123456789')
client=TestClient(create_app(settings))
cases=json.loads((ROOT/'data/evaluation.json').read_text(encoding='utf-8'))
results=[]
for case in cases:
    key=settings.operations_key if case['role']=='operaciones' else settings.risk_key
    response=client.post('/api/v1/query',headers={'X-API-Key':key},json={'question':case['question'],'top_k':3})
    response.raise_for_status();data=response.json();ids=[s['id'] for s in data['sources']]
    results.append({**case,'retrieved':ids,'hit_at_1':bool(ids and ids[0]==case['expected_document']),
                    'hit_at_3':case['expected_document'] in ids,'latency_ms':data['latency_ms']})
n=len(results)
report={'executed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'mode':'extractive','top_k':3,'threshold':settings.threshold,'n_queries':n,
        'corpus_sha256':client.app.state.retriever.corpus_sha256,
        'hit_at_1':sum(x['hit_at_1'] for x in results)/n,
        'hit_at_3':sum(x['hit_at_3'] for x in results)/n,
        'api_latency_ms_median':statistics.median(x['latency_ms'] for x in results),
        'api_latency_ms_max':max(x['latency_ms'] for x in results),
        'limitations':'Corpus y consultas sintéticos de desarrollo; un documento esperado por pregunta. No mide fidelidad generativa, latencia de red, concurrencia ni productividad bancaria.',
        'cases':results}
out=ROOT/'evidence/generated';out.mkdir(parents=True,exist_ok=True)
(out/'retrieval_evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='cases'},ensure_ascii=False,indent=2))
raise SystemExit(0 if report['hit_at_3']>=0.95 else 1)
