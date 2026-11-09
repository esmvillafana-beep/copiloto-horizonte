"""Archiva evidencias generadas localmente para agregarlas al repositorio."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
root=Path(__file__).resolve().parents[1]
files=list((root/'evidence/generated').glob('*'))
if not files:raise SystemExit('No hay evidencias generadas.')
with ZipFile(root/'evidence/evidencias_locales.zip','w',ZIP_DEFLATED) as z:
    for path in files:
        if path.is_file():z.write(path,path.name)
print('Creado evidence/evidencias_locales.zip; revisa que no contenga datos sensibles antes de publicarlo.')
