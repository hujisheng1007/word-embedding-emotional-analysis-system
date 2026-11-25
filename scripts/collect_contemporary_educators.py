"""Run an auditable, metadata-only discovery batch for 15 additional people."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from app.services.collection_service import CollectionService
from app.schemas.collection import CollectionJobCreate

ROOT=Path(__file__).resolve().parents[1]
PEOPLE=['张桂梅','于漪','李吉林','魏书生','窦桂梅','李镇西','于永正','斯霞','霍懋征','顾明远','支月英','张玉滚','陈立群','黄大年','李保国']
def main():
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    backup=Path.home()/'Desktop'/f'教育家采集备份_{stamp}.db'
    with sqlite3.connect(ROOT/'data/app.db') as source, sqlite3.connect(backup) as dest:source.backup(dest)
    service=CollectionService();sources={s.adapter_key:s.id for s in service.list_sources()}
    report={'backup':str(backup),'people':PEOPLE,'scope':'公开新闻RSS索引；标题包含姓名；仅元数据，人物相关性与转载待审','jobs':[]}
    out=ROOT/'backend/runtime/collection'/f'contemporary_{stamp}.json'
    for name in PEOPLE:
        group='当代教育家候选' if name in ['于漪','李吉林','顾明远'] else '优秀教师报道候选'
        jid=service.create_job(CollectionJobCreate(source_id=sources['news_rss'],query=name,educator_name=name,limit=3,research_group=group))
        service.run_job(jid)
        job=next(j for j in service.list_jobs(200) if j.id==jid)
        report['jobs'].append(job.model_dump(mode='json'))
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(name,job.status,job.success_count,job.duplicate_count,job.error_message[:120],flush=True)
    with sqlite3.connect(ROOT/'data/app.db') as db:
        report['resource_counts']=db.execute('select resource_type,count(*),sum(fulltext_allowed),sum(length(extracted_text)) from research_resources group by resource_type').fetchall()
        report['total_resources']=db.execute('select count(*) from research_resources').fetchone()[0]
        report['biography_resource_share']=14/report['total_resources']
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2));print('REPORT',out,flush=True)
if __name__=='__main__':main()
