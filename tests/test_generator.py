import json
import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.config import Settings
from app.generation import ChatGenerator, GenerationUnavailable
from app.main import create_app

OPS='test-operaciones-only-not-production-123'
RISK='test-riesgos-only-not-production-456'
SETTINGS=Settings(OPS,RISK,mode='llm',llm_base_url='http://llm.test/v1',llm_api_key='contract-test-secret')
SOURCES=[{'id':'DOC-001','title':'Contraseña','version':'2.0','text':'Usa el portal de autoservicio.'}]
ORIGINAL_ASYNC_CLIENT=httpx.AsyncClient

def mocked_client(handler):
    def factory(*args,**kwargs):
        kwargs['transport']=httpx.MockTransport(handler)
        return ORIGINAL_ASYNC_CLIENT(*args,**kwargs)
    return factory

class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_compatible_http_contract(self):
        def handler(request):
            self.assertEqual(str(request.url),'http://llm.test/v1/chat/completions')
            self.assertEqual(request.headers['Authorization'],'Bearer contract-test-secret')
            payload=json.loads(request.content)
            self.assertEqual(payload['model'],'qwen2.5:1.5b')
            self.assertEqual(payload['temperature'],0)
            self.assertEqual(len(json.loads(payload['messages'][1]['content'])['fuentes']),1)
            return httpx.Response(200,json={'choices':[{'message':{'content':'Usa el portal [DOC-001].'}}]})
        with patch('app.generation.httpx.AsyncClient',side_effect=mocked_client(handler)):
            result=await ChatGenerator(SETTINGS).answer('¿Cómo restablecer contraseña?',SOURCES)
        self.assertIn('[DOC-001]',result)

    async def check_failure(self,handler):
        with patch('app.generation.httpx.AsyncClient',side_effect=mocked_client(handler)):
            with self.assertRaises(GenerationUnavailable):
                await ChatGenerator(SETTINGS).answer('¿Cómo restablecer contraseña?',SOURCES)

    async def test_missing_citation(self):
        await self.check_failure(lambda req:httpx.Response(200,json={'choices':[{'message':{'content':'Texto sin referencia.'}}]}))
    async def test_unknown_citation(self):
        await self.check_failure(lambda req:httpx.Response(200,json={'choices':[{'message':{'content':'Respuesta [DOC-999].'}}]}))
    async def test_unauthorized_citation(self):
        await self.check_failure(lambda req:httpx.Response(200,json={'choices':[{'message':{'content':'Respuesta [DOC-010].'}}]}))
    async def test_empty_generation(self):
        await self.check_failure(lambda req:httpx.Response(200,json={'choices':[{'message':{'content':''}}]}))
    async def test_invalid_response_schema(self):
        await self.check_failure(lambda req:httpx.Response(200,json={'choices':[]}))
    async def test_provider_500(self):
        await self.check_failure(lambda req:httpx.Response(500,json={'error':'unavailable'}))
    async def test_timeout(self):
        def timeout(req):raise httpx.ReadTimeout('simulado',request=req)
        await self.check_failure(timeout)
    async def test_invalid_json(self):
        await self.check_failure(lambda req:httpx.Response(200,text='not json'))

class GenerationEndpointTests(unittest.TestCase):
    def test_generator_failure_returns_503(self):
        class FailingGenerator:
            async def answer(self,question,sources): raise GenerationUnavailable('simulado')
        client=TestClient(create_app(SETTINGS,FailingGenerator()))
        result=client.post('/api/v1/query',headers={'X-API-Key':OPS},json={'question':'¿Cómo solicitar vacaciones?'})
        self.assertEqual(result.status_code,503)
        self.assertNotIn('contract-test-secret',result.text)

    def test_only_authorized_context_reaches_generator(self):
        captured=[]
        class CapturingGenerator:
            async def answer(self,question,sources):
                captured.extend(sources)
                return 'Respuesta de prueba ['+sources[0]['id']+']'
        client=TestClient(create_app(SETTINGS,CapturingGenerator()))
        result=client.post('/api/v1/query',headers={'X-API-Key':OPS},json={'question':'¿Cómo solicitar vacaciones?'})
        self.assertEqual(result.status_code,200)
        self.assertTrue(captured)
        self.assertTrue(all('operaciones' in s['roles'] for s in captured))
        self.assertNotIn('DOC-010',[s['id'] for s in captured])
        self.assertEqual(result.json()['mode'],'llm')
