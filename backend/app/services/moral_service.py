from datetime import datetime
from hashlib import sha256
import json
import re
from uuid import uuid4

from sqlalchemy import inspect, select, update, func
from sqlalchemy.exc import IntegrityError

from app.db.session import get_session_factory
from app.db.research_models import ResearchResource, ResourceSegment, EducatorPerson
from app.db.moral_models import MoralEvent, MoralRun, MoralReview
from app.schemas.moral import Coding, BuildEvents, CreateEvent, ReviewEvent
from app.engines.moral.engine import COMPONENTS, VERSION, MoralLLMEngine, rule_codes, validate_evidence


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

class MoralSchemaNotReady(RuntimeError):
    pass

class ReviewConflict(RuntimeError):
    pass

class MoralService:
    def __init__(self, session_factory=None, llm=None):
        self.factory=session_factory or get_session_factory()
        self.llm=llm or MoralLLMEngine()

    def check(self):
        with self.factory() as s:
            missing={'moral_events','moral_runs','moral_reviews'}-set(inspect(s.get_bind()).get_table_names())
        if missing:
            raise MoralSchemaNotReady('Rest模块尚未迁移。请先备份数据库，再执行 alembic upgrade head。')

    def catalog(self):
        self.check()
        with self.factory() as s:
            rows=s.execute(select(ResearchResource,EducatorPerson.display_name,func.count(ResourceSegment.id))
                .outerjoin(EducatorPerson,ResearchResource.educator_person_id==EducatorPerson.id)
                .outerjoin(ResourceSegment,ResourceSegment.resource_id==ResearchResource.id)
                .group_by(ResearchResource.id,EducatorPerson.display_name).order_by(ResearchResource.title)).all()
            return [{'id':r.id,'title':r.title,'educator_name':name or '未关联人物',
                     'resource_type':r.resource_type,'segment_count':n,
                     'analyzable':bool(r.fulltext_allowed and n),
                     'source_institution':r.source_institution} for r,name,n in rows]

    def create(self, payload: CreateEvent, selection_method='manual', selection_config=None):
        self.check()
        with self.factory() as s:
            resource=s.get(ResearchResource,payload.resource_id)
            if resource is None:
                raise ValueError('资源不存在')
            if not resource.fulltext_allowed:
                raise ValueError('该资源未登记正文分析许可')
            wanted=set(payload.segment_ids)
            spans=s.scalars(select(ResourceSegment).where(ResourceSegment.resource_id==resource.id,
                ResourceSegment.id.in_(wanted)).order_by(ResourceSegment.ordinal)).all()
            if len(spans)!=len(wanted):
                raise ValueError('片段不存在或不属于同一资源')
            if any(b.ordinal!=a.ordinal+1 for a,b in zip(spans,spans[1:])):
                raise ValueError('事件窗口必须由连续片段构成')
            if sum(len(x.text) for x in spans)>16000:
                raise ValueError('当前单事件上限为16000字符，请缩小窗口')
            person=s.get(EducatorPerson,resource.educator_person_id) if resource.educator_person_id else None
            source_spans=[{'segment_id':x.id,'ordinal':x.ordinal,'text':x.text,
                          'locator_type':x.locator_type,'locator_value':x.locator_value,
                          'text_sha256':sha256(x.text.encode()).hexdigest()} for x in spans]
            # Stable under later metadata edits; changed source text produces a new event.
            fingerprint=sha256(dump({'resource_id':resource.id,'spans':source_spans}).encode()).hexdigest()
            old=s.scalar(select(MoralEvent).where(MoralEvent.fingerprint==fingerprint))
            if old:return {'id':old.id,'created':False}
            snapshot={'resource_id':resource.id,'resource_title':resource.title,
                      'educator_name':person.display_name if person else '未关联人物',
                      'educator_id':resource.educator_person_id,'resource_type':resource.resource_type,
                      'source_institution':resource.source_institution,'source_url':resource.source_url,
                      'data_version':resource.data_version,'selection_method':selection_method,
                      'analysis_modality':'字幕/文本' if resource.resource_type=='video' else '文本',
                      'boundary_status':'待核对主体、上下文与事件边界','spans':source_spans,
                      'selection_config':selection_config or {}}
            event=MoralEvent(id=str(uuid4()),resource_id=resource.id,fingerprint=fingerprint,
                             snapshot_json=dump(snapshot),eligibility='candidate',review_revision=0)
            s.add(event)
            try:s.commit()
            except IntegrityError:
                s.rollback()
                old=s.scalar(select(MoralEvent).where(MoralEvent.fingerprint==fingerprint))
                if old:return {'id':old.id,'created':False}
                raise
            return {'id':event.id,'created':True}

    def build(self,payload:BuildEvents):
        self.check();results=[];skipped=[]
        for rid in dict.fromkeys(payload.resource_ids):
            with self.factory() as s:
                resource=s.get(ResearchResource,rid)
                if resource is None or not resource.fulltext_allowed:
                    skipped.append({'resource_id':rid,'reason':'资源不存在或未登记正文分析许可'});continue
                segments=s.scalars(select(ResourceSegment).where(ResourceSegment.resource_id==rid)
                    .order_by(ResourceSegment.ordinal)).all()
                keywords=list(dict.fromkeys(k for k in re.split(r'[，,、;；\s]+',payload.keyword) if k))
                candidates=[i for i,x in enumerate(segments) if not keywords or
                            sum(x.text.count(k) for k in keywords)>=payload.min_keyword_hits]
                if not candidates:
                    skipped.append({'resource_id':rid,'reason':'没有符合条件的原文片段'});continue
                n=min(payload.per_resource,len(candidates))
                centers=[candidates[min(len(candidates)-1,int((j+.5)*len(candidates)/n))] for j in range(n)]
                windows=[];used=set()
                for c in centers:
                    before=payload.before if payload.before is not None else payload.radius
                    after=payload.after if payload.after is not None else payload.radius
                    ids=[x.id for x in segments[max(0,c-before):c+after+1]]
                    if used.intersection(ids):continue
                    used.update(ids);windows.append(ids)
            for ids in windows:
                try:
                    results.append(self.create(CreateEvent(resource_id=rid,segment_ids=ids),
                        'keyword_even_positions' if payload.keyword else 'even_positions',
                        selection_config=payload.model_dump(exclude={'resource_ids'})))
                except ValueError as exc:skipped.append({'resource_id':rid,'reason':str(exc)})
        return {'items':results,'created':sum(x['created'] for x in results),'skipped':skipped,
                'note':'等位置候选窗口用于试编码；尚未进行语义事件识别，也不是代表性随机样本。'}

    def list_events(self,resource_id='',limit=100,offset=0):
        self.check()
        with self.factory() as s:
            query=select(MoralEvent)
            if resource_id:query=query.where(MoralEvent.resource_id==resource_id)
            total=s.scalar(select(func.count()).select_from(query.subquery()))
            events=s.scalars(query.order_by(MoralEvent.created_at.desc(),MoralEvent.id).offset(offset).limit(limit)).all()
            return {'items':[self.summary(x) for x in events],'total':total}

    @staticmethod
    def summary(event):
        data=json.loads(event.snapshot_json)
        return {'id':event.id,'resource_id':event.resource_id,'resource_title':data['resource_title'],
                'educator_name':data['educator_name'],'resource_type':data['resource_type'],
                'eligibility':event.eligibility,'review_revision':event.review_revision,
                'excerpt':' '.join(x['text'] for x in data['spans'])[:180],
                'created_at':event.created_at.isoformat()}

    @staticmethod
    def run_view(run):
        return {'id':run.id,'event_id':run.event_id,'method':run.method,'status':run.status,
                'config':json.loads(run.config_json),'result':json.loads(run.result_json),
                'error':run.error,'created_at':run.created_at.isoformat()}

    def detail(self,event_id):
        self.check()
        with self.factory() as s:
            event=s.get(MoralEvent,event_id)
            if not event:raise ValueError('事件不存在')
            runs=s.scalars(select(MoralRun).where(MoralRun.event_id==event_id).order_by(MoralRun.created_at.desc()).limit(30)).all()
            reviews=s.scalars(select(MoralReview).where(MoralReview.event_id==event_id).order_by(MoralReview.revision.desc())).all()
            return {**self.summary(event),'snapshot':json.loads(event.snapshot_json),'input_hash':event.fingerprint,
                    'runs':[self.run_view(x) for x in runs],
                    'reviews':[{'id':x.id,'revision':x.revision,'reviewer':x.reviewer,
                                'eligibility':x.eligibility,'codes':json.loads(x.codes_json),'note':x.note,
                                'created_at':x.created_at.isoformat()} for x in reviews]}

    def context(self,event_id,radius=3):
        detail=self.detail(event_id);spans=detail['snapshot']['spans']
        with self.factory() as s:
            rows=s.scalars(select(ResourceSegment).where(ResourceSegment.resource_id==detail['resource_id'],
                ResourceSegment.ordinal>=spans[0]['ordinal']-radius,
                ResourceSegment.ordinal<=spans[-1]['ordinal']+radius).order_by(ResourceSegment.ordinal)).all()
            return [{'segment_id':x.id,'ordinal':x.ordinal,'text':x.text,
                     'locator_type':x.locator_type,'locator_value':x.locator_value} for x in rows]

    def analyze(self,event_id,method):
        if method not in {'rule','llm_direct','llm_evidence'}:raise ValueError('不支持的分析方法')
        detail=self.detail(event_id)
        if detail['eligibility']=='excluded':raise ValueError('已排除事件不参与分析')
        spans=detail['snapshot']['spans']
        run_id=str(uuid4());config={'codebook_version':VERSION,'input_hash':detail['input_hash'],'method':method}
        with self.factory() as s:
            s.add(MoralRun(id=run_id,event_id=event_id,method=method,status='running',config_json=dump(config),result_json='{}',raw_output='',error=''));s.commit()
        raw=''
        try:
            if method=='rule':
                coding=rule_codes(spans);raw=coding.model_dump_json()
            else:
                raw,metadata=self.llm.analyze(spans,method);config.update(metadata)
                coding=Coding.model_validate_json(raw)
            coding=validate_evidence(coding,spans,require_evidence=method!='llm_direct')
            result=coding.model_dump()
            result['review_status']='pending'
            result['citation_check']='not_required' if method=='llm_direct' else 'passed'
            result['semantic_support']='待人工核验'
            error='';status='succeeded'
        except Exception as exc:
            # No fallback to rule results; failed runs remain visible in the audit trail.
            result={};status='failed'
            error=str(exc)[:1600] if isinstance(exc,ValueError) else f'{type(exc).__name__}：模型请求失败，请检查连接或服务状态'
        with self.factory() as s:
            run=s.get(MoralRun,run_id);run.status=status;run.result_json=dump(result)
            run.raw_output=raw;run.config_json=dump(config);run.error=error;s.commit()
            return self.run_view(run)

    def review(self,event_id,payload:ReviewEvent):
        detail=self.detail(event_id)
        if payload.eligibility=='excluded' and not payload.note:
            raise ValueError('排除事件请记录原因')
        coding=Coding(codes=payload.codes)
        validate_evidence(coding,detail['snapshot']['spans'])
        with self.factory() as s:
            updated=s.execute(update(MoralEvent).where(MoralEvent.id==event_id,
                MoralEvent.review_revision==payload.expected_revision).values(
                review_revision=payload.expected_revision+1,eligibility=payload.eligibility))
            if updated.rowcount!=1:
                raise ReviewConflict('此事件已被更新，请重新载入后复核')
            s.add(MoralReview(id=str(uuid4()),event_id=event_id,revision=payload.expected_revision+1,
                reviewer=payload.reviewer,eligibility=payload.eligibility,
                codes_json=dump([c.model_dump() for c in coding.codes]),note=payload.note))
            s.commit()
        return self.detail(event_id)

    def stats(self):
        self.check()
        with self.factory() as s:
            events=s.scalars(select(MoralEvent)).all()
            reviews=s.scalars(select(MoralReview).order_by(MoralReview.revision)).all()
            latest={r.event_id:r for r in reviews}
            counts={c['id']:{k:0 for k in ['supported','not_mentioned','insufficient','counterevidence','mixed']} for c in COMPONENTS}
            by_person={};reviewed=0
            for e in events:
                snap=json.loads(e.snapshot_json)
                name=snap['educator_name'];key=snap.get('educator_id') or e.resource_id
                person=by_person.setdefault(key,{'name':name,'events':0,'confirmed':0})
                person['events']+=1
                if e.eligibility!='confirmed' or e.id not in latest:continue
                reviewed+=1;person['confirmed']+=1
                for c in json.loads(latest[e.id].codes_json):counts[c['component_id']][c['status']]+=1
            failed=s.scalar(select(func.count()).select_from(MoralRun).where(MoralRun.status=='failed'))
            return {'events':len(events),'confirmed':reviewed,'candidate':sum(e.eligibility=='candidate' for e in events),
                    'excluded':sum(e.eligibility=='excluded' for e in events),'failed_runs':failed,
                    'people':list(by_person.values()),'component_counts':counts,
                    'denominator':reviewed,'note':'仅统计已确认事件的最新人工编码；候选、失败和排除不进入分母。'}

    def export(self):
        self.check()
        with self.factory() as s:ids=list(s.scalars(select(MoralEvent.id).order_by(MoralEvent.created_at)))
        return {'format_version':VERSION,'exported_at':datetime.utcnow().isoformat(),
                'codebook':COMPONENTS,'statistics':self.stats(),
                'events':[self.detail(eid) for eid in ids],
                'limitations':['辅助复核模式，尚非盲法独立编码','候选窗口不等于完整事件','字幕分析不等于视听融合']}
