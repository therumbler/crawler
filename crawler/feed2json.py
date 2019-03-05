"""Simple method of converting an RSS/Atom feed into JSON Feed format. https://jsonfeed.org"""
import logging
import defusedxml.ElementTree as ET

logger = logging.getLogger(__name__)

NAMESPACES = {
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'feed': 'http://www.w3.org/2005/Atom',
}


def _find_both(element, tag_name):
    tag = element.find(tag_name, NAMESPACES)
    if tag is None:
        tag = element.find(f'feed:{tag_name}', NAMESPACES)
    return tag.text



def _get_published_date(item_obj):
    tags = ['pubDate', 'feed:published', 'updated']
    published_date = None
    for tag in tags:
        try:
            published_date = item_obj.find(tag, NAMESPACES).text
        except AttributeError:
            pass
    if not published_date:
        logger.error('cannot find published_date')
    return published_date

def _item_parser(item_obj):
    """this should work for <item> (RSS) and <entry> (Atom) tags"""
    item = {}
    #item['id'] = _find_both(item_obj, 'guid')
    try:
        item['id'] = item_obj.find('guid', NAMESPACES).text
    except AttributeError:
        item['id'] = item_obj.find('feed:id', NAMESPACES).text
    item['url'] = _find_both(item_obj, 'link')
    item['title'] = _find_both(item_obj, 'title')
    try:
        item['content_html'] = _find_both(item_obj, 'description').strip()
    except AttributeError:
        # Atom entry? use content field
        logger.info('getting feed:content...')
        item['content_html'] = item_obj.find('feed:content', NAMESPACES).text.strip()
        logger.info('got feed:content.')
    item['published_date'] = _get_published_date(item_obj)
    
    enclosure = item_obj.find('enclosure')
    
    if enclosure is not None:
        if 'attachments' not in item:
            item['attachments'] = []
        size_in_bytes = None
        try:
            size_in_bytes = int(enclosure.attrib['length'])
        except KeyError as ex:
            pass
        
        attachment = {
            'size_in_bytes': size_in_bytes,
            'url': enclosure.attrib['url'],
            'mime_type': enclosure.attrib['type']
        }
        item['attachments'].append(attachment)
    
    return item


def _rss_parser(tree, feed):
    # TODO: favicon check?
    logger.info('in _rss_parser...')
    channel = tree.find('channel')
    feed['title'] = channel.find('title').text
    feed['home_page_url'] = channel.find('link').text
    feed['description'] = channel.find('description').text
    
    try:
        feed['author'] = channel.find('itunes:author', NAMESPACES).text
    except AttributeError:
        pass
    
    for item_obj in channel.findall('item'):
        item = _item_parser(item_obj)
        feed['items'].append(item)
    
    return feed

def _atom_parser(tree, feed):
    logger.info('in _atom_parser getting feed:title ...')
    feed['title'] = tree.find('feed:title', NAMESPACES).text
    logger.info('got feed:title.')
    for entry_obj in tree.findall('feed:entry', NAMESPACES):
        item = _item_parser(entry_obj)
        feed['items'].append(item)
    return feed

def feed2json(feed_string: str) -> dict:
    logger.info('in feed2json...')
    feed = {
        'version' : 'https://jsonfeed.org/version/1',
        'items': []
    }
    try:
        tree = ET.fromstring(feed_string)
    except Exception as ex:
        logger.error('cannot parse feed_string')
        logger.exception(ex)
        return None
    if tree.tag == 'rss':
        parser = _rss_parser
    elif 'feed' in tree.tag:
        parser = _atom_parser
    else:
        raise Exception('cannot find a parser for %s', tree.tag)

    feed = parser(tree, feed)
    logger.info('finished feed2json.')
    return feed