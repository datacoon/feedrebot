#!/usr/bin/env python
# -*- coding: utf8 -*-

import sys
import urllib.request, urllib.error, urllib.parse
from urllib.parse import urljoin, urlparse
from bs4 import UnicodeDammit
from lxml.html import fromstring
import feedparser
from pprint import pprint


def decode_html(html_string):
    converted = UnicodeDammit(html_string, isHTML=True)
    if not converted.str:
        raise UnicodeDecodeError("Failed to detect encoding, tried [%s]", ', '.join(converted.triedEncodings))
    return converted.str


class FeedsExtractor:
    def __init__(self):
        pass

    def __get_page(self, url):
        realurl = None
        f = urllib.request.urlopen(url)
        data = f.read()
        realurl = f.geturl()
        f.close()
        root = fromstring(data)
        return root, realurl

    def __find_rss_autodiscover(self, root, url):
        """Autodiscover feeds by link"""
        feeds = []
        links = root.xpath('//link')
        for link in links:
            if 'rel' in link.attrib and link.attrib['rel'].lower() == 'alternate':
                item = {}
                item['url'] = link.attrib['href']
                if 'type' in link.attrib:
                    ltype = link.attrib['type'].lower()
                    if ltype == 'application/atom+xml':
                        item['feedtype'] = 'atom'
                    elif ltype == 'application/rss+xml':
                        item['feedtype'] = 'rss'
                    else:
                        continue
                if 'title' in link.attrib: item['title'] = link.attrib['title']
                item['confidence'] = 1
                feeds.append(item)
        return feeds


    def __find_feed_img(self, root, url):
        """Find by RSS image"""
        feeds = []
        for img in root.xpath('//img'):
            if 'src' in img.attrib:
                href = img.attrib['src']
                up = urlparse(href)
                ipath = up.path
                parts = ipath.split('/')
                parts.reverse()
                if len(parts) > 1:
                    name = parts[0] if len(parts[0]) > 0 else parts[1]
                else:
                    name = parts[0]
                name = name.lower()
                for k in ['rss', 'feed']:
                    if name.find(k) == 0 and name.find('feedback') == -1:
                        atag = img.getparent()
                        if atag.tag == 'a':
                            u = atag.attrib['href']
                            if u not in feeds:
                                item = {'url': u}
                                text = None
                                if 'title' in atag.attrib: text = atag.attrib['title']
                                if not text and 'alt' in atag.attrib: text = atag.attrib['alt']
                                if not text and 'title' in img.attrib: text = img.attrib['title']
                                if not text and 'alt' in img.attrib: text = img.attrib['alt']
                                if text is not None: item['title'] = text
                                if k == 'rss':
                                    item['feedtype'] = 'rss'
                                else:
                                    item['feedtype'] = 'undefined'
                                item['confidence'] = 0.5
                                feeds.append(item)
        return feeds


    def __find_feed_by_urls(self, root, url):
        "Find feeds by related urls"
        feeds = []
        for olink in root.xpath('//a'):
            item = {}
            feedfound = False
            if 'href' in olink.attrib:
                href = olink.attrib['href']
                up = urlparse(href)
                ipath = up.path
                parts = ipath.split('/')
                parts.reverse()
                if len(parts) > 1:
                    name = parts[0] if len(parts[0]) > 0 else parts[1]
                else:
                    name = parts[0]
                name = name.lower()
                if name.find('.') > -1:
                    name, ext = name.rsplit('.', 1)
                else:
                    ext = ''
                for k in ['rss', 'feed']:
                    if name.find(k) == 0 and name.find('feedback') == -1:
                        u = olink.attrib['href']
                        if u not in feeds:
                            item['url'] = u
                            if k == 'rss':
                                item['feedtype'] = 'rss'
                            else:
                                item['feedtype'] = 'undefined'
                            item['confidence'] = 0.5
                            feeds.append(item)
                            feedfound = True
                            break
                if feedfound: continue
                for p in parts:
                    if p in ['rss', 'feed']:
                        u = olink.attrib['href']
                        if u not in feeds:
                            item['url'] = u
                            if p == 'rss':
                                item['feedtype'] = 'rss'
                            else:
                                item['feedtype'] = 'undefined'
                            item['confidence'] = 0.5
                            feeds.append(item)
                            feedfound = True
                            break
                if feedfound: continue
                text = olink.text
                if text:
                    if text.lower().find('rss') > -1:
                        u = olink.attrib['href']
                        if u not in feeds:
                            item['url'] = u
                            item['confidence'] = 0.5
                            item['feedtype'] = 'rss'
                            feeds.append(item)
                            feedfound = True
                            break
                if feedfound: continue
                for k in ['rss', 'xml']:
                    if ext.find(k) == 0:
                        if olink.getparent().tag == 'a':
                            u = olink.attrib['href']
                            if u not in feeds:
                                item['url'] = u
                                if k == 'rss':
                                    item['feedtype'] = 'rss'
                                else:
                                    item['feedtype'] = 'undefined'
                                item['confidence'] = 0.5
                                feeds.append(item)
                                feedfound = True
                                break
                if feedfound: continue
        return feeds


    def __collect_feeds(self, root, url):
        urls = []
        feeds = self.__find_rss_autodiscover(root, url)
        for f in feeds:
            urls.append(f['url'])
        for u in self.__find_feed_img(root, url):
            if u['url'] not in urls:
                urls.append(u['url'])
                feeds.append(u)
        for u in self.__find_feed_by_urls(root, url):
            if u['url'] not in urls:
                urls.append(u['url'])
                feeds.append(u)
        res = []
        for f in feeds:
            f['url'] = urljoin(url, f['url'])
            res.append(f)
        #        feeds = [urljoin(url, u) for f in feeds]
        return res


    def find_feeds(self, url):
        items = []
        root, real_url = self.__get_page(url)
        results = {'url': real_url, 'items': items}
        if not root:
            return {}
        feeds = self.__collect_feeds(root, real_url)
        for f in feeds:
            items.append(f)
        results['items'] = items
        return results

    def find_feeds_deep(self, url, lookin=True):
        items = []
        root, real_url = self.__get_page(url)
        results = {'url': real_url, 'items': items}
        if not root:
            return {}
        feeds = self.__collect_feeds(root, real_url)
        for f in feeds:
            pprint(f)
            d = feedparser.parse(f['url'])
            if 'title' in d.feed:
                items.append({'title': d.feed.title, 'url': f['url'], 'feedtype': f['feedtype']})
            elif lookin:
                dp, dp_url = self.__get_page(f['url'])
                if not dp:
                    results['items'] = items
                    return results
                cfeeds = self.__collect_feeds(dp, dp_url)
                for cf in cfeeds:
                    d = feedparser.parse(cf['url'])
                    if 'title' in d.feed:
                        items.append(cf)
        results['items'] = items
        return results


if __name__ == "__main__":
    import sys
    feeds = FeedsExtractor().find_feeds_deep(sys.argv[1])
    pprint(feeds)
#    FeedsExtractor().identify_gks_sites()
#    FeedsExtractor().identify_arbitr_sites()
#    FeedsExtractor().process_sites()
#    FeedsExtractor().update_charsets()
