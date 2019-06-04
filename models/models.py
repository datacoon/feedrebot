
# -*- coding: utf-8 -*-
from mongoengine import *

FEED_MODE_DIGEST = 1
FEED_MODE_FULL = 2

FEED_TYPE_RSS = 10
FEED_TYPE_HTML = 20

class User(Document):
    userid = StringField(required=True, max_length=50, unique=True)
    name = StringField(max_length=100)
    max_ch = IntField(default=3)
    fd_per_ch = IntField(default=5)

class Channel(Document):
    chid = StringField(required=True, max_length=50, unique=True)
    user = ReferenceField(User)
    name = StringField(max_length=100)

class Feed(Document):
    feedid = StringField(required=True, max_length=50)
    user = ReferenceField(User)
    feedmode = IntField(default=FEED_MODE_DIGEST)
    channel = ReferenceField(Channel)
    url = StringField(max_length=1000, required=True)
    feedtype = IntField(default=FEED_TYPE_RSS)
    lastpost_guid = StringField(max_length=500)
    last_updated = DateTimeField()

class Post(Document):
    postid = StringField(required=True, max_length=1000)
    feed = ReferenceField(Feed)
    title = StringField(max_length=1000, required=True)
    description = StringField(max_length=100000, required=True)
    author = StringField(max_length=1000)
    url = StringField(max_length=1000)
    published = DateTimeField()
    isposted = BooleanField(default=False)