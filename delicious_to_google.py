#!/usr/bin/env python

"""
Methods to import del.icio.us posts into Google Reader.
Gets posts with 'blog' tag, gets feeds for them, creates OPML document.
"""

import urllib, urllib2
import xml.etree.ElementTree as ET
from BeautifulSoup import BeautifulSoup

# set timeout in seconds
import socket
socket.setdefaulttimeout(60)

import conf

auth_handler = urllib2.HTTPBasicAuthHandler()
auth_handler.add_password(
    conf.del_realm, conf.del_host, conf.del_username, conf.del_password)
opener = urllib2.build_opener(auth_handler)
urllib2.install_opener(opener)

# del.icio.us helper methods

# def getTags():
#     "call del.icio.us get tags method"
#     url_type = 'tags'
#     url_method = 'get'
#     url = '/'.join((del_url_base, url_type, url_method))
#     f = urllib2.urlopen(url)
#     return f.read()

def getAll(tag=None):
    """
    Call del.icio.us get all posts method.
    Use sparingly, this gets us throttled
    """
    url_type = 'posts'
    url_method = 'all'
    url = '/'.join((conf.del_url_base, url_type, url_method))
    args = {}
    if tag:
        args = {'tag':tag}
    f = urllib2.urlopen(url, urllib.urlencode(args))
    return f.read()

def makeFeedURL(blog_url, feed_url):
    "make feed URL, combining with blog_url in the case of a relative URL"
    if feed_url[:7] != 'http://':
        # relative url
        if feed_url[0] == '/':
            # relative root url, add blog_url up to domain, skip /
            url_base = blog_url[:blog_url.find('/', 7)]
            return url_base + feed_url
        else:
            # relative url, add blog_url, make sure to have /
            if blog_url[-1] != '/':
                feed_url = '/' + feed_url
            feed_url = blog_url + feed_url
    return feed_url

def getFeeds(blogs_xml):
    """
    yield atom or rss feed URLs from blog URLs in blogs_xml
    """
    for post in ET.fromstring(blogs_xml):
        blog_href = post.get('href')
        try:
            href = post.get('href')
            blog_stream = urllib2.urlopen(href)
            # must use a loose parser on HTML intended for browsers
            # tried using ET on the prettified BS parse tree, still choked
            blog_tree = BeautifulSoup(blog_stream)
            head = blog_tree.html.head
            feed_links = head.findAll(name='link', **{'rel':'alternate'})
            atom_urls = [l['href'] for l in feed_links
                         if l['type'] == 'application/atom+xml']
            rss_urls = [l['href'] for l in feed_links
                        if l['type'] == 'application/rss+xml']
            feed_url = None
            if atom_urls:
                feed_url = atom_urls[0]
            elif rss_urls:
                feed_url = rss_urls[0]
            if feed_url:
                yield makeFeedURL(href, feed_url)
        except IOError, urllib2.URLError:
            # bad URL or timeout
            continue
        except AttributeError:
            # bad HTML
            continue
        except KeyError:
            # no type attr in the link?  Not sure why this happens.
            continue
        except TypeError:
            # apparently a urllib2 bug
            # TypeError: 'HTTPError' object is not callable
            continue

def feedsToOPML(feeds):
    "Given iterator of feed URLs, return OPML document."
    root = ET.Element('opml')
    root.set('version', '1.0')
    head = ET.SubElement(root, 'head')
    body = ET.SubElement(head, 'body')
    for feed_str in feeds:
        outline = ET.SubElement(body, 'outline')
        outline.set('xmlUrl', feed_str)
    #tree = ET.ElementTree(root)
    return ET.tostring(root)

blogs_out = getAll(tag='blog')
feed_gen = getFeeds(blogs_out)
opml = feedsToOPML(feed_gen)
print opml
