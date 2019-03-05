import logging
from urllib.parse import urlparse

import aiohttp
from requests_html import HTML


logger = logging.getLogger(__name__)


def _get_absolute_link(from_url: str, relative_url: str):
    """return a full url based on a relative url"""
    if relative_url.startswith('http'):
        return relative_url
    try:
        u = urlparse(from_url)
        full_url = f'{u.scheme}://{u.netloc}{relative_url}'
    except Exception as ex:
        logger.error('cannot urlparse from_url "%s" ; relative_url "%s"', from_url, relative_url)
        logger.exception(ex)
        return None
    return full_url

def _is_text(content_type):
    types = ['text', 'xml', 'rss']
    for _type in types:
        if _type in content_type:
            return True
    logger.debug('content_type "%s" is not text', content_type)
    return False



async def fetch(session, url):
    async with session.head(url) as resp:
        try:
            content_type = resp.headers['Content-Type']
        except KeyError as ex:
            logger.error('cannot find Content-Type for url %s', url)
            try:
                # could be a re-redirect
                location = resp.headers['Location']
                logger.info('got a Location header: %s', location)
                
                full_url = _get_absolute_link(url, location)
                return await fetch(session, full_url)
            except KeyError as ex:
                logger.error('no location header for url %s', url)
                return None

    if not _is_text(content_type):
        return None

    logger.info('fetching %s ...', url)
    async with session.get(url) as resp:
        text = await resp.text('utf-8')
        logger.debug('loaded %s bytes from %s', len(text), url)
        return text


async def get_links(session, url):
    logger.debug('in get_links...')
    html_string = await fetch(session, url)
    if not html_string:
        return None, None

    html_obj = HTML(html=html_string, url=url)
    
    urls = html_obj.absolute_links
    feeds = set()
    links = html_obj.find('link')
    logger.debug('found %d link tags...', len(list(links)))
    for link in links:
        if 'type' in link.attrs:
            if 'rss+xml' in link.attrs['type']:
                feed_url = link.attrs['href']
                
                if not feed_url.startswith('http'):
                    feed_url = _get_absolute_link(url, feed_url)
                
                if feed_url:
                    logger.debug('found rss url %s', feed_url)
                    feeds.add(feed_url)
        
    logger.debug('got %d new links and %s feeds from %s', len(list(urls)), len(list(feeds)), url)
    return urls, feeds