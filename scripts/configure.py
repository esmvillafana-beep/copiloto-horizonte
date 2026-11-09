"""Crea claves locales sin imprimirlas; compatible con Windows, macOS y Linux."""
import secrets
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'.env'
if path.exists():
    raise SystemExit('.env ya existe. Se conserva para evitar sobrescribir credenciales.')
text=(root/'.env.example').read_text(encoding='utf-8')
text=text.replace('OPERACIONES_API_KEY=','OPERACIONES_API_KEY='+secrets.token_urlsafe(32),1)
text=text.replace('RIESGOS_API_KEY=','RIESGOS_API_KEY='+secrets.token_urlsafe(32),1)
path.write_text(text,encoding='utf-8')
try:
    path.chmod(0o600)
except OSError:
    pass
print('Configuración creada en .env. Consulta las claves solo en tu editor local.')
