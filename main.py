#!/usr/bin/env python3
"""An attempt at a web crawler
https://docs.python.org/3/library/asyncio-queue.html
"""
import asyncio
import logging
import sys

import aiohttp

from crawler import get_links
from crawler.crawler import fetch
from crawler.feed2json import feed2json

logger = logging.getLogger(__name__)

def setup_logging(level=logging.DEBUG):
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(pathname)s - %(funcName)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

COMPLETED_URLS = set()

async def feed_worker(name, queue, session):
    logger.info('launching feed_worker %s', name)

    while True:
        feed_url = await queue.get()
        if feed_url in COMPLETED_URLS:
            logger.info('already fetched %s', feed_url)
            continue

        try:
            logger.info('%s fetching url %s ...', name, feed_url)
            feed_string = await fetch(session, feed_url)
            logger.info('fetched url %s', feed_url)
            
            json_feed = feed2json(feed_string)
            if not json_feed:
                logger.error('unable to parse feed_url %s', feed_url)
        
            COMPLETED_URLS.add(feed_url)
        except Exception as ex:
            logger.exception(ex)
        
async def worker(name, queue, feed_queue, session):
    logger.debug('launching worker %s', name)
    while True:
        url = await queue.get()
        logger.debug('worker %s fetching url %s ...', name, url)
        if url in COMPLETED_URLS:
            logger.info('already fetched %s', url)
            continue
        links, feeds = await get_links(session, url)
        COMPLETED_URLS.add(url)
        logger.debug('worker %s fetched url %s.', name, url)
        if not links:
            continue

        for link in links:
            await queue.put(link)

        for feed_url in feeds:
            logger.debug('found feed url %s', feed_url)
            await feed_queue.put(feed_url)

async def main():
    """let's do it!"""
    setup_logging(level=logging.DEBUG)
   
    queue = asyncio.Queue()
    feed_queue = asyncio.Queue()
    start_urls = ['https://www.hvper.com', 'https://alltop.com']
    
    for start_url in start_urls:
        queue.put_nowait(start_url)
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        logger.debug('session created')
        #links, feeds = await get_links(session, 'https://irumble.com/beatswithbenji')
        #print(feeds)
        #feed_string = await fetch(session, 'https://irumble.com/beatswithbenji/feed.xml')
        # feed_url = 'https://daringfireball.net/feeds/main'
        # feed_url = 'https://mjtsai.com/blog/feed/'
        # feed_url = 'https://www.tomshardware.com/feeds/rss2/all.xml'
        # feed_url = 'https://feeds.abcnews.com/abcnews/topstories'
        # feed_string = await fetch(session, feed_url)
        # json_feed = await feed2json(feed_string)
        # print(json_feed['items'][0])
        # return
        tasks = []
        task = asyncio.create_task(feed_worker(f'feed_worker-1', feed_queue, session))
        tasks.append(task)
        for i in range(10):
            task = asyncio.create_task(worker(f'worker-{i}', queue, feed_queue, session))
            tasks.append(task)

        await queue.join()

    await asyncio.gather(*tasks, return_exceptions=True)
if __name__ == "__main__":
    asyncio.run(main())