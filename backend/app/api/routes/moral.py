from fastapi import APIRouter, HTTPException, Query
from app.schemas.moral import BuildEvents, CreateEvent, AnalyzeEvent, ReviewEvent
from app.services.moral_service import MoralService, MoralSchemaNotReady, ReviewConflict
from app.engines.moral.engine import COMPONENTS, VERSION
router=APIRouter(prefix='/moral',tags=['moral-narrative-evidence'])
service=MoralService()

def call(fn,*args,**kwargs):
    try:return fn(*args,**kwargs)
    except MoralSchemaNotReady as exc:raise HTTPException(503,str(exc)) from exc
    except ReviewConflict as exc:raise HTTPException(409,str(exc)) from exc
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@router.get('/codebook')
def codebook():return {'version':VERSION,'components':COMPONENTS,'stage':'试编码，待专家审查'}
@router.get('/resources')
def resources():return call(service.catalog)
@router.get('/stats')
def stats():return call(service.stats)
@router.get('/export')
def export():return call(service.export)
@router.get('/events')
def events(resource_id:str='',limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0)):
    return call(service.list_events,resource_id,limit,offset)
@router.post('/events/build')
def build(payload:BuildEvents):return call(service.build,payload)
@router.post('/events')
def create(payload:CreateEvent):return call(service.create,payload)
@router.get('/events/{event_id}')
def detail(event_id:str):return call(service.detail,event_id)
@router.get('/events/{event_id}/context')
def context(event_id:str):return call(service.context,event_id)
@router.post('/events/{event_id}/analyze')
def analyze(event_id:str,payload:AnalyzeEvent):return call(service.analyze,event_id,payload.method)
@router.post('/events/{event_id}/reviews')
def review(event_id:str,payload:ReviewEvent):return call(service.review,event_id,payload)

@router.post('/events/{event_id}/legacy-analysis')
def legacy_analysis(event_id:str):
    from app.services.analysis_service import AnalysisService
    detail=call(service.detail,event_id)
    text='\n\n'.join(x['text'] for x in detail['snapshot']['spans'])
    return AnalysisService()._analyze_from_text(text,use_llm=False).model_dump()
