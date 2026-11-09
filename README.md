# Copiloto Operativo para Empleados de Banco Horizonte Digital

Proyecto académico de Esmeralda Villafaña, matrícula 07183692. Gestión de Proyectos de Inteligencia Artificial, Universidad Tecmilenio. Banco Horizonte Digital y todos los procedimientos del corpus son ficticios.

El prototipo ofrece una interfaz web, API FastAPI, recuperación documental con permisos por rol y conexión opcional a un LLM. No ejecuta operaciones bancarias. Cada respuesta requiere revisión humana.

## Estado verificable

- Ejecutado en el entorno de elaboración: 70 pruebas automatizadas de Python y TestClient, sin fallos; 24 consultas sintéticas de desarrollo con Hit@1 y Hit@3 de 100 %; ocho comprobaciones HTTP reales contra Uvicorn local.
- El adaptador del LLM se probó con transporte simulado. Esto **no** constituye inferencia con pesos reales.
- Pendiente: construcción y ejecución Docker, ejecución generativa real, publicación en GitHub y resultado real de Actions. El despliegue en Render se documenta como procedimiento; no se afirma que exista un servicio publicado.
- No se completó una prueba de navegador automatizada en el entorno de elaboración porque no está instalado el binario de Chromium. El script opcional está incluido. La comprobación GET de la interfaz no equivale a una prueba de interacción en navegador.

Los resultados originales están en `evidence/baseline/`. Las nuevas ejecuciones se guardan en `evidence/generated/`, excluido de Git. No se deben presentar resultados pendientes como ejecutados.

## Inicio rápido

Requisitos: Python 3.12, Git y Docker Desktop con Compose v2. Primero descomprime y abre una terminal en esta carpeta.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

```bash
python -m pip install -r requirements-lock.txt
python scripts/configure.py
python scripts/run_tests.py
python scripts/evaluate.py
python scripts/verify_local.py
```

`configure.py` genera `.env` con dos claves aleatorias. No imprime ni sobrescribe claves. Para una segunda ejecución, no repitas configure.py si `.env` ya existe. Las claves visibles en las pruebas son exclusivamente de prueba; no son credenciales de producción.

Ejecución sin Docker:

```bash
python scripts/start_local.py
```

Abre http://127.0.0.1:8000. Consulta en tu editor local la clave `OPERACIONES_API_KEY` de `.env` y úsala en la interfaz. Documentación: http://127.0.0.1:8000/docs. Detén con Ctrl+C. En Swagger, usa Authorize para configurar X-API-Key y prueba POST /api/v1/query.

## Docker y evidencia

Con Docker Desktop en funcionamiento y `.env` creado:

```bash
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
python scripts/verify_docker.py
```

`verify_docker.py` exige que la API esté en modalidad extractiva. Comprueba el ID de la imagen, el contenedor healthy, el usuario sin root, ocho consultas HTTP y la suite dentro de un contenedor de pruebas. Si Docker no está disponible, falla de forma explícita. Los resultados nuevos son `docker_verification.json`, `container_http.json` y `container_tests.txt` en `evidence/generated/`.

```bash
docker compose logs --tail 50 api
docker compose down
```

## Generación real con Ollama

```bash
docker compose --profile llm up -d ollama
docker compose exec ollama ollama pull qwen2.5:1.5b
```

Modifica `.env`:

```ini
ANSWER_MODE=llm
LLM_BASE_URL=http://ollama:11434/v1
LLM_MODEL=qwen2.5:1.5b
LLM_API_KEY=
LLM_TIMEOUT=90
```

```bash
docker compose up -d --force-recreate api
python scripts/smoke_http.py --expected-mode llm --output llm_live.json
```

No se expone el puerto de Ollama en el host. La API sí puede acceder al servicio por la red de Compose. La etiqueta `ollama/ollama:latest` es mutable; registra el digest de la imagen realmente utilizada y el modelo instalado como parte de tu evidencia. Para despliegues controlados, fija ese digest después de verificarlo:

```bash
docker image inspect ollama/ollama:latest --format "{{json .RepoDigests}}"
docker compose exec ollama ollama list
```

Revisa las respuestas contra las fuentes y llena `docs/REVISION_GENERATIVA.csv`. Un identificador válido no demuestra que la afirmación sea verdadera. El modelo de 1.5B es una elección inicial para demostración; su calidad en español y fidelidad deben medirse antes de aceptarlo. Si no supera la evaluación, cambia a un modelo mayor y repite la validación con los recursos necesarios.

## Arquitectura y contrato

Interfaz web → API autenticada → controles de consulta → índice del rol → recuperación → respuesta extractiva o LLM → referencias y revisión humana.

- `GET /health`: público; vivacidad de API y corpus cargado. No comprueba disponibilidad del LLM.
- `GET /api/v1/documents`: requiere X-API-Key; catálogo autorizado.
- `POST /api/v1/query`: requiere X-API-Key.
- `GET /docs` y `/openapi.json`: contrato público, sin datos del corpus ni claves.

```json
{"question":"¿Cómo restablecer la contraseña corporativa?","top_k":1}
```

Estados de negocio: `answered`, `no_evidence`, `blocked`. Códigos: 200 solicitud procesada, 401 credencial inválida, 422 entrada inválida, 503 fallo del LLM o respuesta no validada. Pregunta de 5 a 1000 caracteres; top_k entero de 1 a 3; campos extra rechazados.

La respuesta incluye `request_id`, `status`, `answer`, `sources`, `mode`, `requires_human_review` y `latency_ms`. Cada fuente tiene ID, título, versión, fecha de aprobación ficticia, extracto y similitud. `score` no es una probabilidad de exactitud.

El corpus contiene 12 documentos vigentes y uno sustituido. Operaciones accede a 11 vigentes y Riesgos a 10. Se filtran permisos antes de construir el índice. La recuperación es **léxica TF-IDF**, no semántica por embeddings. En modo `extractive` no se usa un LLM. En modo `llm` se llama a `/chat/completions` bajo la URL base configurada. Un fallo del generador devuelve 503; no hay cambio de modalidad silencioso.

## Despliegue en Render

Consulta `docs/MANUAL_DESPLIEGUE.md`. El Blueprint `render.yaml` crea la API Docker, configura `/health` y genera dos claves secretas. Arranca en modalidad extractiva. Revisa recursos y condiciones de la plataforma antes de aceptar cargos.

Para probar la URL de nube, carga la clave de **nube** en una variable temporal. En PowerShell puedes introducirla sin dejar su valor en el historial:

```powershell
$claveTemporal = Read-Host "Clave Operaciones de nube" -AsSecureString
$env:CLOUD_OPERACIONES_KEY = [System.Net.NetworkCredential]::new("", $claveTemporal).Password
python scripts/smoke_http.py --base-url https://DOMINIO-REAL.onrender.com --key-env CLOUD_OPERACIONES_KEY --output cloud_smoke.json
Remove-Item Env:CLOUD_OPERACIONES_KEY
Remove-Variable claveTemporal
```

Sustituye el dominio. Para modo generativo agrega `--expected-mode llm`. En ese modo Render necesita un proveedor accesible por HTTPS, p. ej. una API compatible en `https://ollama.com/v1`, una clave y un modelo habilitado en la cuenta. No uses `http://ollama:11434/v1` en Render: ese nombre solo existe en Compose local. No se ejecuta Compose dentro de Render.

## Publicación en GitHub

Crea un repositorio vacío con tu cuenta y cambia USUARIO por su identificador real:

```bash
git init
git branch -M main
git add .
git commit -m "Implementa prototipo del copiloto operativo para Fase II"
git remote add origin https://github.com/USUARIO/copiloto-horizonte.git
git push -u origin main
```

No publiques `.env`. Si el repositorio es privado, concede acceso al docente. El workflow prueba Python y Docker en un runner Ubuntu. Aún no ha sido ejecutado en GitHub en esta entrega; conserva su resultado real después del push. No incluye una prueba real de LLM, que requiere descargar el modelo y revisar sus respuestas por separado.

## Prueba opcional de interfaz con navegador

```bash
python -m pip install -r requirements-browser.txt
python -m playwright install chromium
python scripts/verify_browser.py
```

Inicia un servidor temporal en 8766 y verifica la interacción real de la interfaz. Guarda JSON y dos capturas con el campo de clave vacío. No forma parte de las 70 pruebas originales. Requiere instalar Chromium; no se da por ejecutada.

## Evidencias para entregar

```bash
python scripts/package_evidence.py
```

El archivo resultante `evidence/evidencias_locales.zip` puede agregarse al repositorio después de revisar su contenido. No contiene `.env`. Incluye el enlace real de GitHub, el commit, la evidencia Docker, la prueba de LLM y la revisión humana. Una respuesta favorable de health no basta para demostrar todo el funcionamiento.

## Seguridad y límites

Solo material ficticio. Claves por rol para demostración, sin SSO, identidad individual, límites de consumo o garantía de detección de ataques. No hay carga de documentos ni historial persistente. El corpus solo cambia mediante una nueva versión del código y de la imagen. Se requiere una evaluación institucional antes de tratar información real. Las 24 preguntas son de desarrollo y no constituyen una evaluación externa. No se han medido productividad, ROI, concurrencia o disponibilidad de producción.

Documentación: `docs/MANUAL_DESPLIEGUE.md`, `docs/VALIDACION_PRUEBAS.md`, `docs/DOCUMENTACION_ASISTIDA.md` y `docs/REVISION_GENERATIVA.csv`.
