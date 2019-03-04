#!/usr/bin/env python3
"""An attempt at a web crawler
https://docs.python.org/3/library/asyncio-queue.html
"""
import asyncio
import logging
import sys

import aiohttp

from crawler import get_links

logger = logging.getLogger(__name__)

def setup_logging(level=logging.DEBUG):
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(pathname)s - %(funcName)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

async def worker(name, queue, session):
    logger.info('launcing worker %s', name)
    while True:
        url = await queue.get()
        logger.info('worker %s fetching url %s ...', name, url)
        links = await get_links(session, url)
        for link in links:
            await queue.put(link)

async def main():
    """let's do it!"""
    setup_logging(level=logging.INFO)
   
    queue = asyncio.Queue()
    queue.put_nowait('https://www.hvper.com')
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(10):

            task = asyncio.create_task(worker(f'worker-{i}', queue, session))
            tasks.append(task)

        await queue.join()


    await asyncio.gather(*tasks)
if __name__ == "__main__":
    asyncio.run(main())