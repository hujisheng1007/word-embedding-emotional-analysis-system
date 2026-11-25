"""Public news RSS discovery. Stores titles/links only, never article bodies."""
import xml.etree.ElementTree as ET
from .base import Candidate, HttpAdapter

class NewsRSSAdapter(HttpAdapter):
    key = 'news_rss'
    def search(self, query, limit=10, **options):
        response=self.client.get('https://news.google.com/rss/search',params={'q':f'"{query}"','hl':'zh-CN','gl':'CN','ceid':'CN:zh-Hans'})
        response.raise_for_status()
        root=ET.fromstring(response.content)
        items=[]
        for item in root.findall('./channel/item'):
            title=item.findtext('title') or ''
            if query.casefold() not in title.casefold():continue
            url=item.findtext('link') or ''
            if not url.startswith('https://'):continue
            items.append(Candidate(kind='webpage',external_id=url,title=title,source_name=item.findtext('source') or '新闻 RSS',source_url=url,educator_name=options.get('educator_name',query),metadata={'discovery':'news_rss','relevance':'title_name_match_pending_review'},access_level='public',restriction_reason='新闻索引元数据；未采集正文，转载与原始发布者需要人工核查'))
            if len(items)>=limit:break
        return items
