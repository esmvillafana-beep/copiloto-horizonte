# Validación y pruebas

## 7 Documento de validación y pruebas

### Método y criterios de aceptación

Organicé la validación en pruebas de configuración, API, recuperación, permisos, entradas extremas e integración del generador. El corpus contiene exclusivamente material sintético y las 24 consultas de evaluación fueron elaboradas para el desarrollo. No constituyen un conjunto externo o independiente.

Establecí los siguientes criterios: la suite automatizada debe terminar sin fallos; las solicitudes sin credencial deben recibir 401; las entradas inválidas deben recibir 422; los documentos restringidos y sustituidos no deben aparecer en los resultados; las consultas sin contexto deben producir abstención; y el documento esperado debe aparecer entre los tres primeros resultados en al menos 95 % de las consultas de desarrollo. Este último umbral evalúa recuperación y no equivale a la meta de respuestas fundamentadas del piloto de Fase I.

### Entorno de ejecución

Las pruebas se ejecutaron con Python 3.12.14, FastAPI 0.141.1, Uvicorn 0.52.1, HTTPX 0.28.1, Pydantic 2.13.4 y scikit-learn 1.8.0. Las versiones directas y transitivas se registran en requirements-lock.txt y la evidencia incluye la huella SHA-256 del corpus. Las fechas de los archivos de evidencia se expresan en UTC; la fecha de este documento corresponde al 8 de noviembre en Ciudad de México.

El entorno no dispone de daemon Docker ni de sesión autenticada en GitHub. Por ello, las pruebas realizadas no se describen como validación de contenedor ni como ejecución de GitHub Actions. Tampoco se descargaron ni ejecutaron pesos de un modelo de lenguaje.

### Resultados funcionales

| Evidencia ejecutada | Resultado | Interpretación |
|---|---|---|
| Suite automatizada | 70 pruebas, 0 fallos y 0 errores | Los casos definidos pasaron en Python y TestClient. |
| HTTP local con Uvicorn | 8 comprobaciones correctas | La API responde por red en un proceso real, sin Docker. |
| Recuperación de desarrollo | 24 de 24 consultas con documento esperado en primer lugar | Hit@1 y Hit@3 de 100 % en este corpus. |
| Credenciales y permisos | Casos de rechazo y aislamiento superados | Se verifica la separación de los dos roles en las pruebas definidas. |
| Adaptador generativo | Contrato y fallos controlados con transporte simulado | Se valida integración de código; no calidad de un LLM real. |

Los 70 casos incluyen 24 consultas de recuperación y 46 pruebas adicionales de contrato, configuración, límites y fallos. Las 24 consultas también se analizan en el reporte de evaluación; no las cuento como 24 pruebas independientes adicionales para inflar el total.

La prueba HTTP local realizó GET /health, GET /, una consulta sin clave, una entrada inválida, una pregunta con documento, una abstención, una solicitud bloqueada y una consulta al catálogo. Las solicitudes autenticadas fueron enviadas al servidor Uvicorn; no se sustituyeron por respuestas prefabricadas.

### Métricas de recuperación

Definí Hit@k como el número de consultas cuyo documento esperado aparece entre los k primeros resultados, dividido entre el total de consultas. Cada pregunta tiene un único documento esperado y se utiliza top_k=3. En esta evaluación, Hit@1 = 24/24 = 100 % y Hit@3 = 24/24 = 100 %.

La mediana del tiempo interno de procesamiento de la API fue 0.69 ms y el máximo fue 1.532 ms durante esas 24 consultas. Los valores excluyen el tiempo de red, el navegador y la inferencia generativa. Corresponden a una ejecución breve y no deben interpretarse como un compromiso de servicio.

El resultado es coherente con la sencillez del corpus y la cercanía del vocabulario entre preguntas y documentos. No permite concluir que el sistema comprenderá cualquier paráfrasis, que será preciso con manuales reales o que superará a una búsqueda semántica. La prueba de fidelidad de respuestas generativas queda pendiente.

### Casos extremos y manejo de errores

| Caso evaluado | Comportamiento esperado | Resultado ejecutado |
|---|---|---|
| Clave ausente o incorrecta | HTTP 401 | Superado. |
| Pregunta vacía, espacios o menos de 5 caracteres | HTTP 422 | Superado. |
| Más de 1,000 caracteres | HTTP 422 | Superado. |
| Entrada de 1,000 caracteres | Aceptación y limpieza del texto | Superado. |
| top_k fuera de 1 a 3 o de tipo incorrecto | HTTP 422 | Superado. |
| Campo role añadido por el cliente | HTTP 422 | Superado. |
| JSON mal formado | HTTP 422 | Superado. |
| Pregunta sobre temperatura de Marte | no_evidence y sin fuentes | Superado. |
| Pregunta ambigua sin contexto | no_evidence | Superado. |
| Documento reservado a otro rol | Exclusión de contenido y referencia restringidos | Superado en los casos definidos. |
| Versión histórica sustituida | Exclusión del resultado | Superado. |
| Patrón explícito de inyección de instrucciones | blocked y sin fuentes | Superado para el patrón probado. |
| Número sintético de 16 dígitos | blocked sin repetir el número | Superado para el patrón probado. |
| Solicitud de aprobación de crédito | blocked | Superado para el patrón probado. |
| Timeout o error 500 del proveedor | Excepción controlada y HTTP 503 | Superado con simulación. |
| Cita inexistente, ausente o no autorizada del LLM | Rechazo de la respuesta | Superado con simulación. |

Los filtros de seguridad son reglas ilustrativas. No detectan todas las variantes de inyección, solicitudes sensibles o datos personales. Tampoco sustituyen un sistema DLP, una evaluación adversarial ni controles de identidad institucional. La protección principal de recuperación consiste en filtrar permisos en el servidor antes de construir y consultar el índice.

### Validación generativa que debe completarse

Antes de afirmar que el sistema generativo quedó validado debo ejecutar el modelo real y revisar al menos las 24 preguntas de desarrollo, varias preguntas sin respuesta y ataques de inyección reformulados. Para cada respuesta registraré si el procedimiento indicado es correcto, si toda afirmación relevante tiene respaldo en el contexto, si la referencia corresponde a la versión recuperada y si se mantiene el límite de actuación del copiloto.

El registro de revisión humana se prepara en docs/REVISION_GENERATIVA.csv y no contiene resultados prellenados. Calcularé la proporción de respuestas fundamentadas como respuestas totalmente respaldadas entre respuestas revisadas, y la proporción de referencias verificables como referencias que corresponden a un documento y versión existentes entre referencias revisadas. Las metas de al menos 95 % y 98 %, respectivamente, provienen de la Fase I y siguen pendientes de medición generativa.

Una respuesta con una recomendación operativa peligrosa, un acceso indebido o una política inventada debe tratarse como hallazgo crítico, aunque otras métricas sean favorables. También necesito ampliar las pruebas con un corpus y preguntas revisados por especialistas que no hayan intervenido en la construcción del prototipo.

## 8 Correspondencia con la rúbrica y evidencias pendientes

| Criterio y peso | Material preparado | Verificación pendiente |
|---|---|---|
| Contenerización y despliegue local 25 % | Dockerfile, Compose y script de comprobación | Construir y ejecutar la imagen; conservar evidencia healthy y consultas desde el contenedor. |
| Integración técnica 25 % | Frontend, API, contrato y control de permisos | Completar inferencia con LLM real y conservar su evidencia. |
| Pruebas y validación 25 % | 70 pruebas automatizadas, evaluación documental y HTTP | Revisar fidelidad generativa y ampliar casos externos. |
| Documentación y repositorio 25 % | Código, README, manual, validación y flujo de CI | Publicar en GitHub y registrar la ejecución real de Actions. |

El despliegue efectivo en la nube se describe como un procedimiento replicable; la instrucción solicita un manual, no permite atribuir un despliegue inexistente. Si realizo la publicación en Render, agregaré la URL real y su evidencia para fortalecer la demostración.

Antes de la entrega final debo incorporar el enlace de GitHub y el commit evaluado; los archivos docker_verification.json, container_http.json y container_tests.txt; el resultado de llm_live.json y la revisión humana de las respuestas; y el enlace de GitHub Actions o sus artefactos. También puedo añadir capturas de la interfaz con respuesta y fuentes, de Swagger y del servicio Docker healthy. En ninguna captura deben aparecer las claves.

