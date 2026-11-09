"""Arranque local sin Docker; lee .env, sin bibliotecas adicionales."""
import os
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
for line in (root/'.env').read_text(encoding='utf-8').splitlines():
    if line.strip() and not line.lstrip().startswith('#'):
        key,value=line.split('=',1)
        os.environ.setdefault(key.strip(),value.strip())
import uvicorn
if __name__=='__main__':
    uvicorn.run('app.main:app',factory=True,host='127.0.0.1',port=int(os.getenv('PORT','8000')))
