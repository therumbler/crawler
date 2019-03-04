import logging

import aiohttp
from requests_html import HTML


logger = logging.getLogger(__name__)

async def fetch(session, url):
    logger.debug('fetching %s ...', url)
    async with session.get(url) as resp:
        return await resp.text()

async def get_links(session, url):
    logger.debug('in get_links...')
    html_string = await fetch(session, url)
    
    html_obj = HTML(html=html_string, url=url)
    urls = html_obj.absolute_links
    logger.debug('got %d new links from %s', len(list(urls)), url)
    return urls