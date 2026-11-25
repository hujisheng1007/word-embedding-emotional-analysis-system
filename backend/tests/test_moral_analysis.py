from pathlib import Path
import json
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db import moral_models, research_models
from app.db.moral_models import MoralRun
from app.schemas.moral import BuildEvents, CreateEvent, ReviewEvent, Coding
from app.services.moral_service import MoralService, ReviewConflict
from app.services.research_resource_service import ResearchResourceService
from app.engines.moral.engine import rule_codes, validate_evidence

@pytest.fixture()
def services(tmp_path):
    engine=create_engine(f'sqlite:///{tmp_path / "rest.db"}')
    @event.listens_for(engine,'connect')
    def fk(dbapi, _):dbapi.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    resources=ResearchResourceService(factory,tmp_path/'storage')
    ids=[]
    for n,text in [('甲','老师发现学生面临辍学风险。\n\n他认为每个学生都应有学习的机会。\n\n他协调学校安排帮助。'),('乙','人们称赞他很高尚。\n\n他计划以后资助学生。\n\n材料没有交代实施结果。')]:
        r=resources.import_file(filename=n+'.txt',data=text.encode(),title=n+'教育事件',resource_type='book',
            educator_name=n,source_url='https://example.edu/'+n,fulltext_allowed=True,
            copyright_status='authorized',access_level='internal')
        ids.append(r.resource_id)
    return MoralService(factory),ids

def build_one(service,rid):
    return service.build(BuildEvents(resource_ids=[rid],per_resource=1))['items'][0]['id']

def test_build_across_people_is_idempotent_and_keeps_source_snapshot(services):
    s,ids=services
    result=s.build(BuildEvents(resource_ids=ids,per_resource=1))
    assert result['created']==2
    assert s.build(BuildEvents(resource_ids=ids,per_resource=1))['created']==0
    assert len(s.stats()['people'])==2
    d=s.detail(result['items'][0]['id'])
    assert d['eligibility']=='candidate' and d['snapshot']['spans'][0]['locator_value']
    with s.factory() as db:
        segment=db.get(research_models.ResourceSegment,d['snapshot']['spans'][0]['segment_id'])
        segment.text='后续改动';db.commit()
    assert s.detail(d['id'])['snapshot']==d['snapshot']

def test_cross_resource_and_non_contiguous_spans_are_rejected(services):
    s,ids=services
    with s.factory() as db:
        spans=list(db.scalars(select(research_models.ResourceSegment).where(research_models.ResourceSegment.resource_id==ids[0]).order_by(research_models.ResourceSegment.ordinal)))
        other=db.scalar(select(research_models.ResourceSegment).where(research_models.ResourceSegment.resource_id==ids[1]))
    with pytest.raises(ValueError):s.create(CreateEvent(resource_id=ids[0],segment_ids=[other.id]))
    with pytest.raises(ValueError):s.create(CreateEvent(resource_id=ids[0],segment_ids=[spans[0].id,spans[-1].id]))

def test_rule_candidates_do_not_infer_motivation_or_personality(services):
    s,ids=services;eid=build_one(s,ids[1]);run=s.analyze(eid,'rule')
    assert run['status']=='succeeded'
    assert all(c['status'] in {'insufficient','not_mentioned'} for c in run['result']['codes'])
    assert 'score' not in json.dumps(run['result'])
    assert s.stats()['denominator']==0

@pytest.mark.parametrize('quote,start,end',[('编造引文',None,None),('帮助',0,2),('老师帮助学生。',0,9999)])
def test_fabricated_and_wrong_offset_quotes_rejected(quote,start,end):
    spans=[{'segment_id':'s','text':'老师帮助学生。'}];coding=rule_codes(spans)
    c=coding.codes[0];c.status='supported';c.evidence=[]
    from app.schemas.moral import Evidence
    c.evidence=[Evidence(segment_id='s',quote=quote,start_char=start,end_char=end)]
    with pytest.raises(ValueError):validate_evidence(coding,spans)

def test_unicode_and_repeated_quote_offsets():
    from app.schemas.moral import Evidence
    spans=[{'segment_id':'s','text':'𠮷帮助学生，帮助学生。'}];coding=rule_codes(spans)
    c=coding.codes[0];c.status='supported';c.evidence=[Evidence(segment_id='s',quote='帮助学生')]
    with pytest.raises(ValueError):validate_evidence(coding,spans)
    c.evidence[0].start_char=1;c.evidence[0].end_char=5
    assert validate_evidence(coding,spans).codes[0].evidence[0].start_char==1

@pytest.mark.parametrize('bad',['offline','invalid','fabricated'])
def test_llm_failure_is_persisted_without_fallback(services,bad):
    s,ids=services;eid=build_one(s,ids[0])
    class Fake:
        def analyze(self,spans,method):
            if bad=='offline':raise TimeoutError('offline')
            if bad=='invalid':return '{oops',{}
            c=rule_codes(spans).model_dump();c['codes'][0]['status']='supported'
            c['codes'][0]['evidence']=[{'segment_id':spans[0]['segment_id'],'quote':'捏造的历史事实','polarity':'support'}]
            return json.dumps(c),{'model':'fake'}
    s.llm=Fake();run=s.analyze(eid,'llm_evidence')
    assert run['status']=='failed' and run['result']=={}
    assert s.detail(eid)['runs'][0]['method']=='llm_evidence'
    assert s.stats()['failed_runs']==1

def test_reviews_are_versioned_conflicts_rejected_and_stats_use_latest(services):
    s,ids=services;eid=build_one(s,ids[0]);run=s.analyze(eid,'rule')
    codes=run['result']['codes'];d=s.detail(eid);span=d['snapshot']['spans'][0]
    codes[0].update(status='supported',rationale='原文记载主体发现学生风险。',
                    evidence=[{'segment_id':span['segment_id'],'quote':span['text'],'polarity':'support'}])
    payload=ReviewEvent(expected_revision=0,reviewer='编码者A',codes=codes)
    d=s.review(eid,payload)
    assert d['review_revision']==1 and s.stats()['denominator']==1
    with pytest.raises(ReviewConflict):s.review(eid,payload)
    payload.expected_revision=1;payload.eligibility='excluded';payload.note='窗口边界待重建'
    d=s.review(eid,payload)
    assert len(d['reviews'])==2 and s.stats()['denominator']==0
    assert s.stats()['excluded']==1
    assert len(s.export()['events'][0]['reviews'])==2

def test_mixed_status_needs_both_polarities(services):
    s,ids=services;eid=build_one(s,ids[0]);codes=s.analyze(eid,'rule')['result']['codes']
    codes[0]['status']='mixed'
    with pytest.raises(ValueError):s.review(eid,ReviewEvent(expected_revision=0,reviewer='A',codes=codes))

def test_direct_llm_and_evidence_llm_use_distinct_contracts(services):
    s,ids=services;eid=build_one(s,ids[0])
    class Fake:
        def analyze(self,spans,method):
            c=rule_codes(spans).model_dump()
            for x in c['codes']:x.update(status='supported',evidence=[])
            return json.dumps(c),{'model':'fake'}
    s.llm=Fake()
    assert s.analyze(eid,'llm_direct')['status']=='succeeded'
    assert s.analyze(eid,'llm_evidence')['status']=='failed'

def test_asymmetric_keyword_windows_and_threshold(services):
    service,ids=services
    result=service.build(BuildEvents(resource_ids=[ids[0]],keyword='辍学,风险',min_keyword_hits=2,before=0,after=1,per_resource=1))
    assert result['created']==1
    d=service.detail(result['items'][0]['id'])
    assert len(d['snapshot']['spans'])==2
    assert '辍学' in d['snapshot']['spans'][0]['text']
    assert d['snapshot']['selection_config']['after']==1
    empty=service.build(BuildEvents(resource_ids=[ids[0]],keyword='辍学,风险',min_keyword_hits=3))
    assert not empty['items']
