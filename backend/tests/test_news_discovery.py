import httpx
from app.collectors.news import NewsRSSAdapter

def test_news_discovery_filters_names_and_never_imports_fulltext():
    xml='<rss><channel><item><title>张桂梅的课堂</title><link>https://example.org/1</link><source>测试来源</source></item><item><title>无关新闻</title><link>https://example.org/2</link></item></channel></rss>'
    client=httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,text=xml)))
    result=NewsRSSAdapter(client=client).search('张桂梅')
    assert len(result)==1
    assert result[0].educator_name=='张桂梅'
    assert result[0].fulltext_allowed is False
    assert result[0].kind=='webpage'
