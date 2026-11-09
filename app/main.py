"""API y frontend del prototipo académico. Ejecutar con uvicorn app.main:app --factory."""
import logging
import re
import secrets
import time
import unicodedata
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .config import Settings
from .generation import ChatGenerator, GenerationUnavailable
from .retrieval import Retriever

logger = logging.getLogger('copiloto')
api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)

class Query(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    question: str = Field(min_length=5, max_length=1000)
    top_k: int = Field(default=2, ge=1, le=3)

    @field_validator('question')
    @classmethod
    def clean_question(cls, value):
        value=value.strip()
        if len(value)<5 or not any(c.isalpha() for c in value):
            raise ValueError('Escribe una pregunta con al menos cinco caracteres y alguna letra.')
        return value

class Source(BaseModel):
    id: str
    title: str
    version: str
    approved_at: str
    excerpt: str
    score: float

class Answer(BaseModel):
    request_id: str
    status: str
    answer: str
    sources: list[Source]
    mode: str
    requires_human_review: bool = True
    latency_ms: float


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.lower()) if not unicodedata.combining(c))

def blocked_reason(question):
    q=normalize(question)
    # Control ilustrativo y limitado; no es un detector universal de ataques o datos personales.
    if re.search(r'(?<!\d)(?:\d[ -]?){16}(?!\d)',q):
        return 'La consulta parece contener un número sensible. Retira los datos personales.'
    if re.search(r'(ignora|ignore|omite|olvida).{0,45}(instrucciones|reglas|instructions)|system prompt|prompt del sistema|revela.{0,30}(clave|secreto|credencial)',q):
        return 'La solicitud intenta modificar instrucciones o revelar secretos. Solicita revisión humana.'
    if re.search(r'\b(aprueba|aprobar|autoriza|autorizar|ejecuta|ejecutar|transfiere|transferir|modifica|modificar)\b.{0,50}\b(credito|transferencia|saldo|operacion|fondos)\b',q):
        return 'El copiloto no ejecuta operaciones ni autoriza decisiones financieras. Acude a la persona responsable.'
    return None

def create_app(settings=None, generator=None):
    settings=settings or Settings.from_env()
    retriever=Retriever(settings.corpus_path)
    generator=generator or ChatGenerator(settings)

    @asynccontextmanager
    async def lifespan(application):
        yield

    api=FastAPI(title='Copiloto Operativo Horizonte', version='1.0.0', lifespan=lifespan)
    api.state.retriever=retriever
    api.state.settings=settings

    def authenticate(key: Annotated[str | None, Depends(api_key_header)]):
        if key and secrets.compare_digest(key,settings.operations_key):
            return 'operaciones'
        if key and secrets.compare_digest(key,settings.risk_key):
            return 'riesgos'
        raise HTTPException(status_code=401, detail='Credencial ausente o inválida.')

    @api.get('/', include_in_schema=False)
    def home():
        return FileResponse(Path(__file__).parent/'static/index.html')

    @api.get('/health')
    def health():
        # Vivacidad y corpus cargado. No prueba disponibilidad del LLM remoto.
        return {'status':'ok','version':'1.0.0','mode':settings.mode}

    @api.get('/api/v1/documents')
    def documents(role: Annotated[str,Depends(authenticate)]):
        return {'documents':retriever.catalog(role)}

    @api.post('/api/v1/query', response_model=Answer)
    async def query(body:Query, role:Annotated[str,Depends(authenticate)]):
        start=time.perf_counter()
        request_id=str(uuid.uuid4())
        status='answered'
        reason=blocked_reason(body.question)
        sources=[]
        if reason:
            status='blocked'
            answer=reason
        else:
            found=retriever.search(body.question,role,body.top_k,settings.threshold)
            if not found:
                status='no_evidence'
                answer='No encontré evidencia suficiente en las fuentes autorizadas. Consulta a la persona responsable.'
            else:
                sources=[Source(id=s['id'],title=s['title'],version=s['version'],
                                approved_at=s['approved_at'],excerpt=s['text'],score=s['score']) for s in found]
                if settings.mode=='extractive':
                    answer='Referencia documental para revisión humana:\n'+'\n'.join(f"[{s['id']}] {s['text']}" for s in found)
                else:
                    try:
                        answer=await generator.answer(body.question,found)
                    except GenerationUnavailable:
                        # No se presenta una respuesta extractiva como si fuera generativa.
                        raise HTTPException(status_code=503,detail='Generador no disponible o respuesta no validada. Reintenta o escala a revisión humana.')
        latency=round((time.perf_counter()-start)*1000,3)
        logger.info('request_id=%s role=%s status=%s mode=%s latency_ms=%s',request_id,role,status,settings.mode,latency)
        return Answer(request_id=request_id,status=status,answer=answer,sources=sources,
                      mode=settings.mode,latency_ms=latency)
    return api

def app():
    return create_app()
