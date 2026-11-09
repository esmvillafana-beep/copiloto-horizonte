# Manual de despliegue

## 5 Manual de despliegue local y contenerización

### Requerimientos técnicos

| Recurso | Requerimiento o recomendación |
|---|---|
| Sistema operativo | Windows con Docker Desktop y WSL 2, macOS o Linux con Docker Engine. |
| Runtime | Python 3.12 para ejecución sin Docker y scripts de evidencia. |
| Herramientas | Git, Docker con Compose v2 y acceso a terminal. |
| Red | Acceso a los registros de imágenes y a los paquetes de Python durante la construcción. |
| API extractiva | Estimación inicial de 2 núcleos, 2 GB de RAM y 2 GB libres; validar consumo real. |
| Modalidad generativa | Recomendación inicial de 8 GB de RAM total y al menos 5 GB libres; ajustar al modelo. |
| Puerto local | 8000 disponible para la API. Ollama permanece en la red interna de Compose. |

Los recursos anteriores son recomendaciones iniciales para el corpus académico. No representan el resultado de una prueba de capacidad o concurrencia.

### Preparación del entorno

Descomprimiré el paquete y abriré una terminal en la carpeta copiloto-horizonte. Crearé un entorno virtual y lo activaré con el comando correspondiente al sistema operativo.

```bash
python -m venv .venv
```

En PowerShell de Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

En macOS o Linux:

```bash
source .venv/bin/activate
```

A continuación instalaré las dependencias y generaré dos claves distintas:

```bash
python -m pip install -r requirements-lock.txt
python scripts/configure.py
```

El script genera .env con claves aleatorias y no las imprime. Si .env ya existe, se detiene para conservar la configuración. Para probar el rol en la interfaz consultaré su clave únicamente en el editor local. No debo incluir el contenido de .env en capturas, reportes ni commits.

### Ejecución de referencia sin Docker

```bash
python scripts/start_local.py
```

Abriré http://127.0.0.1:8000 e introduciré la clave del rol. Esta ejecución permite revisar la API y la interfaz en Python. No sustituye la evidencia del contenedor exigida por la rúbrica. Para detener el servicio utilizaré Ctrl+C.

Puedo reproducir automáticamente las pruebas locales mediante:

```bash
python scripts/run_tests.py
python scripts/evaluate.py
python scripts/verify_local.py
```

El último comando inicia un servidor temporal en el puerto 8765, ejecuta ocho comprobaciones HTTP reales y lo detiene. Sus resultados se guardan en evidence/generated.

### Construcción y ejecución del contenedor

Con Docker Desktop o Docker Engine en ejecución comprobaré la instalación y construiré el servicio:

```bash
docker version
docker compose version
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
```

El Dockerfile parte de Python 3.12 slim, instala las versiones del archivo de dependencias, copia la aplicación y utiliza el usuario appuser en lugar de root. Uvicorn escucha en 0.0.0.0 y utiliza PORT; si la variable no se define, usa 8000. El servicio de Compose publica el puerto únicamente en la interfaz local 127.0.0.1, monta el sistema de archivos como solo lectura y retira capacidades adicionales del contenedor.

El HEALTHCHECK consulta /health mediante la biblioteca estándar de Python. Debo comprobar que docker compose ps muestre el servicio en ejecución y con estado healthy. Después abriré la interfaz y la documentación de la API en el navegador.

Para reunir evidencia verificable ejecutaré:

```bash
python scripts/verify_docker.py
```

Este script exige un daemon Docker real, identifica la imagen y el contenedor, comprueba el estado healthy y el usuario, realiza consultas HTTP y ejecuta la suite en un contenedor de pruebas. Guarda docker_verification.json, container_http.json y container_tests.txt. Evita inspeccionar o exportar todas las variables del contenedor porque contienen secretos. Si Docker no está disponible, se detiene sin producir evidencia de éxito.

Para revisar la salida del servicio o detenerlo utilizaré:

```bash
docker compose logs --tail 50 api
docker compose down
```

### Activación del modelo generativo local

Con el servicio extractivo comprobado, iniciaré Ollama y descargaré el modelo académico:

```bash
docker compose --profile llm up -d ollama
docker compose exec ollama ollama pull qwen2.5:1.5b
```

Modificaré en .env las variables siguientes, conservando las claves de los roles:

```ini
ANSWER_MODE=llm
LLM_BASE_URL=http://ollama:11434/v1
LLM_MODEL=qwen2.5:1.5b
LLM_API_KEY=
LLM_TIMEOUT=90
```

Recrearé la API para que lea la configuración y probaré la integración real:

```bash
docker compose up -d --force-recreate api
python scripts/smoke_http.py --expected-mode llm --output llm_live.json
```

La API envía la solicitud a /v1/chat/completions, según la compatibilidad documentada por Ollama. El servidor Ollama local no exige una clave de proveedor; su servicio no se publica hacia Internet en esta configuración. La primera inferencia puede tardar por la carga del modelo. Si aparecen errores 503, revisaré la descarga, los registros y la disponibilidad de memoria antes de modificar el tiempo máximo de espera.

La aceptación generativa exige, además del éxito técnico, revisar manualmente si cada afirmación está respaldada por el documento citado. La validación automática de identificadores solo comprueba la pertenencia de las referencias al contexto. Un modelo puede producir una afirmación incorrecta aun cuando cite un identificador válido.

Para conservar las evidencias locales en un archivo compartible ejecutaré:

```bash
python scripts/package_evidence.py
```

## 6 Manual de despliegue en la nube

### Estrategia y preparación

Seleccioné Render como plataforma PaaS para alojar la API mediante el Dockerfile del repositorio. La estrategia permite conservar el mismo código entre la ejecución local y la nube. El archivo render.yaml define el servicio y la ruta de salud. La selección de recursos debe revisarse en la cuenta antes de confirmar el despliegue; no doy por hecho un plan gratuito ni un costo fijo.

Para esta demostración utilizaré exclusivamente el corpus sintético. La publicación de información bancaria real requeriría revisar residencia de datos, contratos, identidad corporativa, retención, cifrado, auditoría y autorización institucional. Esos controles no se consideran implementados mediante este prototipo.

Necesito una cuenta de Render, el repositorio ya publicado y permiso para conectarlo. Recomiendo iniciar la API con una instancia de al menos 1 GB de RAM y ajustar después de observar el consumo. Esta estimación excluye el alojamiento de los pesos del LLM. La modalidad generativa en la nube requiere un servicio de inferencia independiente y accesible desde Render.

### Procedimiento de despliegue

**Paso 1. Verificar el código.** Confirmaré que las pruebas locales pasen, que no se publiquen claves y que el commit de GitHub corresponda a la versión documentada.

**Paso 2. Conectar el repositorio.** En Render iniciaré la creación de un Blueprint y seleccionaré el repositorio copiloto-horizonte. Si la interfaz de la plataforma cambia, utilizaré la opción equivalente para importar render.yaml. Revisaré la configuración antes de autorizar el consumo de recursos.

**Paso 3. Configurar el servicio.** El Blueprint utiliza runtime docker, Dockerfile en la raíz y /health como ruta de comprobación. Genera dos valores secretos distintos para OPERACIONES_API_KEY y RIESGOS_API_KEY. La modalidad inicial es ANSWER_MODE=extractive y el umbral es RETRIEVAL_THRESHOLD=0.18.

**Paso 4. Construir y arrancar.** Confirmaré el despliegue y revisaré los registros. El proceso debe instalar dependencias, cargar el corpus e iniciar Uvicorn. Render establece PORT y la aplicación escucha en 0.0.0.0 para admitir las solicitudes de la plataforma. No debo fijar la API únicamente a 127.0.0.1 dentro del servicio de nube.

**Paso 5. Validar la URL.** Cuando el servicio esté disponible, abriré su dirección HTTPS y /health. Introduciré una clave de rol en la interfaz y comprobaré una pregunta con fuente, una abstención y un bloqueo. El hecho de recibir HTTP 200 de /health no sustituye las consultas funcionales.

**Paso 6. Registrar resultados.** Ejecutaré smoke_http.py con la URL real. La clave de nube debe estar disponible en la variable de entorno indicada, sin reutilizar accidentalmente la clave de una instalación local. El README incluye un ejemplo seguro para introducirla desde PowerShell sin dejarla escrita en el historial.

```bash
python scripts/smoke_http.py --base-url https://URL-REAL-DEL-SERVICIO --key-env CLOUD_OPERACIONES_KEY --output cloud_smoke.json
```

URL-REAL-DEL-SERVICIO es un marcador que debo sustituir por el dominio asignado. Conservaré cloud_smoke.json, el identificador del despliegue, el commit y una captura del servicio activo sin mostrar secretos.

### Modalidad generativa en la nube

El servicio Docker de la API no incluye los pesos de Ollama ni depende de que Render ejecute Compose. Para habilitar generación, configuraré un servidor de inferencia independiente. Una opción compatible documentada es la API de Ollama Cloud en https://ollama.com/v1, con una clave de proveedor y un modelo habilitado en la cuenta. La disponibilidad, el consumo y las condiciones deben comprobarse antes de usarlo.

En la configuración de Render estableceré ANSWER_MODE=llm, LLM_BASE_URL, LLM_MODEL, LLM_API_KEY y LLM_TIMEOUT. Guardaré la clave del proveedor como secreto de ejecución, nunca en el Dockerfile o el repositorio. Después desplegaré nuevamente y ejecutaré smoke_http.py con --expected-mode llm y la URL de nube. Esta ruta transmite el contexto al proveedor; por ello, su uso académico se limita al corpus ficticio.

### Operación y reversión

El corpus se integra en la imagen. Cada modificación documental exige revisar los permisos y la versión, ejecutar las pruebas y desplegar una nueva imagen. La aplicación no guarda conversaciones ni acepta cargas de archivos. Los registros propios incluyen identificador de solicitud, rol, estado, modalidad y tiempo; no incorporan el texto de la pregunta ni las claves.

Ante una regresión, conservaré los registros sin datos sensibles y volveré a desplegar el último commit que haya superado la validación. Si el problema se concentra en el generador, puedo configurar explícitamente ANSWER_MODE=extractive y volver a desplegar. El cambio debe quedar visible en las respuestas; una falla generativa no se transforma silenciosamente en una respuesta atribuida a un LLM.

La aplicación usa claves compartidas por rol para demostrar autorización. Antes de un piloto institucional se requieren identidad individual, autorización centralizada, rotación, límites de consumo y una evaluación de seguridad. También falta evaluar carga, disponibilidad, recuperación ante fallos y políticas de conservación de registros.

### Documentación asistida por inteligencia artificial

Utilicé ChatGPT como apoyo para estructurar el código, revisar la redacción y organizar el manual. No atribuyo a Microsoft Copilot una intervención en esta fase que no se haya realizado. La documentación se contrastó con el comportamiento de las pruebas y con documentación técnica oficial. Conservé la distinción entre explicación sugerida, código implementado y resultado ejecutado.

En docs/DOCUMENTACION_ASISTIDA.md registré la herramienta utilizada, los criterios de revisión y un prompt de reproducción: “Revisa este Dockerfile, contrato de API y manual de despliegue. Identifica inconsistencias entre variables, puertos y comandos. Diferencia capacidades implementadas, pruebas ejecutadas y verificaciones pendientes. No inventes capturas, métricas, enlaces ni resultados”.

La asistencia de IA no reemplaza la revisión del código ni las evidencias. Mi responsabilidad consiste en comprender los comandos, reproducirlos y corregir cualquier discrepancia antes de entregar o desplegar.

