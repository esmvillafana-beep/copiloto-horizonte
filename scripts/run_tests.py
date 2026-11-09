"""Ejecuta unittest y guarda resultados reales con contexto reproducible."""
import datetime
import hashlib
import io
import json
import platform
from pathlib import Path
import sys
import unittest
from importlib.metadata import version
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

class Recorder(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.records=[]
    def addSuccess(self,test):
        super().addSuccess(test);self.records.append({'test':test.id(),'result':'passed'})
    def addFailure(self,test,err):
        super().addFailure(test,err);self.records.append({'test':test.id(),'result':'failed'})
    def addError(self,test,err):
        super().addError(test,err);self.records.append({'test':test.id(),'result':'error'})

if __name__=='__main__':
    out=ROOT/'evidence/generated';out.mkdir(parents=True,exist_ok=True)
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),top_level_dir=str(ROOT))
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Recorder).run(suite)
    log=stream.getvalue();print(log)
    (out/'unittest.txt').write_text(log,encoding='utf-8')
    report={'executed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'environment':{'python':platform.python_version(),'platform':platform.platform(),
                           'packages':{p:version(p) for p in ['fastapi','uvicorn','httpx','scikit-learn','pydantic']}},
            'corpus_sha256':hashlib.sha256((ROOT/'data/corpus.json').read_bytes()).hexdigest(),
            'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'skipped':len(result.skipped),'success':result.wasSuccessful(),'cases':result.records,
            'scope':'Python y TestClient; adaptador LLM con transporte simulado. No prueba Docker ni un LLM real.'}
    (out/'unittest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
