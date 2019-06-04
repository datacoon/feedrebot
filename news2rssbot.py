# -*- coding: utf-8 -*-
import sys
import os
from urllib.parse import urlencode
import requests
from requests.adapters import HTTPAdapter
from pprint import pformat, pprint
import json
from datetime import datetime
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler
import uuid
from models.models import *
from mongoengine import connect
from settings import *

import feedparser
from findfeeds import FeedsExtractor
from newsworker.extractor import FeedExtractor


requests.adapters.DEFAULT_RETRIES = 5

COMMANDS_TEXT = u"""
    Привет! Этот бот создан для создания новостных каналов в Телеграм. Он умеет транслировать публикации из RSS лент 
    и из сайтов где есть новости, но без RSS - бот обладает уникальными алгоритмами извлекающими новости из HTML.
    Бот поддерживает следующие команды:
    - /list - получить список каналов и подписок
    - /channel [идентификатор канала] - добавляет канал для подписки. Название канала нужно передавать без символа '@' вначале. Пример: /channel govdigest
    - /leave [идентификатор канала] - покинуть канал
    - /add [идентификатор канала] [ссылка на веб-страницу] - добавляет подписку ленту к каналу
    - /remove [код подписки] - удалить подписку
    - /update - форсировать обновление лент по Вашим каналам
    - /test [ссылка на веб-страницу] - проверить может ли бот извлечь новости из сайта
    - /help - справочник

    Ошибки направляйте через issues в github - https://github.com/datacoon/feedrebot
    """


def bot_logdebug(update, text):
    if update and BOT_DEBUG:
        now = datetime.now()
        update.message.reply_text('[%d:%d:%d]: %s' % (now.hour, now.minute, now.second, text))

def __verify_feed(url, update=None):
    bot_logdebug(update, 'Запрашиваю страницу по ссылке')
    resp = requests.get(url, headers={'User-agent' : USER_AGENT}, timeout=10)
    headers = resp.headers
    ctype = headers['Content-Type'].split(';', 1)[0].lower()
    logging.info(str(headers))
    feeds = []
    if ctype == 'text/html':
        bot_logdebug(update, 'Обнаружен тип документ: HTML страница')
        afeeds = FeedsExtractor().find_feeds_deep(url)
        logging.info(str(afeeds))
        if 'items' not in afeeds.keys():
            bot_logdebug(update, 'RSS ленты не обнаружены. Проверяем наличие новостей на странице')
            ext = FeedExtractor(filtered_text_length=150)
            data, session = f.get_feed(url)
            logging.info(data)
            if data and len(data['items']) > 0:
                feeds.append({'feedtype' : FEED_TYPE_HTML, 'title' : data['title'], 'num' : len(data['items']), 'url' : url})
                bot_logdebug(update, 'На странице найдено и извлечено %d новостей' % (len(data['items'])))
                return feeds
        else:
            bot_logdebug(update, 'Обнаружены предполагаемые RSS ленты, проверяем каждую по ссылке')
            for f in afeeds['items']:
                feed = feedparser.parse(f['url'])
                if len(feed['entries']) > 0:
                    logging.info(feed)
                    feeds.append({'feedtype': FEED_TYPE_RSS, 'title': feed['feed']['title'], 'num': len(feed['entries']), 'url' : f['url']})
            if len(feeds) == 0:
                bot_logdebug(update, 'На всякий случай проверяем, может быть сама страница это все таки RSS')
                feed = feedparser.parse(resp.content)
                if len(feed['entries']) > 0:
                    logging.info(feed)
                    feeds.append(
                            {'feedtype': FEED_TYPE_RSS, 'title': feed['feed']['title'], 'num': len(feed['entries']),
                             'url': url})
                    return feeds
            else:
                return feeds
            bot_logdebug(update, 'Проверяем на наличие новостей в теле HTML страницы')
            ext = RSSExtractor(filtered_text_length=150)
            data, session = ext.get_rss(url)
            logging.info(data)
            if data and len(data['items']) > 0:
                feeds.append({'feedtype' : FEED_TYPE_HTML, 'title' : data['title'], 'num' : len(data['items']), 'url' : url})
                bot_logdebug(update, 'На странице найдено и извлечено %d новостей' % (len(data['items'])))
                return feeds
    elif ctype in ['application/xml', 'application/rss+xml', 'text/xml']:
        bot_logdebug(update, 'Обнаружен тип документа: XML файл. Проверяем что это RSS')
        feed = feedparser.parse(resp.content)
        if len(feed['entries']) > 0:
            logging.info(feed)
            feeds.append({'feedtype' : FEED_TYPE_RSS, 'title' : feed['feed']['title'], 'num' : len(feed['entries']), 'url' : url})
            return feeds
        pass
    else:
        bot_logdebug(update, 'Обнаружен непонятный тип документа. Проверяем что это RSS')
        feed = feedparser.parse(resp.content)
        if len(feed['entries']) > 0:
            logging.info(feed)
            feeds.append({'feedtype' : FEED_TYPE_RSS, 'title' : feed['feed']['title'], 'num' : len(feed['entries']), 'url' : url})
            return feeds
        pass
    return feeds


def __get_feed_type(feedtype):
    if feedtype == FEED_TYPE_HTML:
        return 'html'
    elif feedtype == FEED_TYPE_RSS:
        return 'rss'
    return 'unknown'

def __get_user(update):
    """Returns Telegram username if exists, overwise user id"""
    try:
        userid = update.effective_user.username
    except:
        userid = str(update['from']['id'])
    try:
        user = User.objects.get(userid=userid)
    except DoesNotExist as ex:
        user = User(userid=userid, name=update.effective_user.name)
        user.save()
    return user

def helpcmd(bot, update):
    update.message.reply_text(COMMANDS_TEXT)



def do_addchannel(bot, update):
    query = update['message']['text']
    chname = query.split(' ', 1)[-1].strip()
    user = __get_user(update)
    len_channels = Channel.objects(user=user).count()
    if len_channels == user.max_ch:
        message = u"Вы достигли максимума каналов %d, Вам надо отписать бот хотя бы от одного" % (len_channels)
    else:
        isadm = False
        try:
            admins = bot.getChatAdministrators('@' + chname)
            logging.info(admins)
            for m in admins:
                if m.user.username == user.userid or m.user.id == user.userid:
                    isadm = True
        except:
            pass
        if isadm:
            try:
                channel = Channel.objects.get(chid=chname)
            except:
                channel = None
            if channel is not None:
                message = u"Канал ранее был добавлен"
            else:
                ch = Channel(user=user, chid=chname)
                ch.save()
                message = u"Канал %s добавлен" % (chname)
        else:
            message = u"Вы должны добавить бот @FeedRetranslatorBot в администраторы канала %s" % (chname)
    update.message.reply_text(message)

def do_leave(bot, update):
    query = update['message']['text']
    chname = query.split(' ', 1)[-1].strip()
    user = __get_user(update)
    channel = Channel.objects(user=user, chid=chname)
    if channel is None:
        message = u"Канал не найден"
    else:
        channel.delete()
        message = u"Канал %s отключен" % (chname)
    update.message.reply_text(message)


def do_add(bot, update):
    query = update['message']['text']
    user = __get_user(update)
    parts = query.split(' ')[1:]
    if len(parts) == 2:
        chname, url = parts
        feedtype = 'rss'
    else:
        message = u'Должны быть переданы 2 параметра: идентификатор канала и ссылка'
        update.message.reply_text(message)
        return
    channel = Channel.objects.get(user=user, chid=chname)
    if channel is None:
        message = u"Канал не найден"
    else:
        feeds = __verify_feed(url, update)
        logging.info(str(feeds))
        if len(feeds) == 0:
            message = u"По ссылке %s не удалось найти RSS ленту и извлечь новости" % (url)
        else:
            af = feeds[0]
            feed = Feed(channel=channel, user=user, feedid=uuid.uuid4().hex, url=af['url'], feedtype=af['feedtype'], feedmode=FEED_MODE_DIGEST)
            feed.save()
            message = u'Подписка к каналу %s добавлена\nid: %s, url: %s' % (channel.chid, feed.feedid, feed.url)
    update.message.reply_text(message)


def do_remove(bot, update):
    query = update['message']['text']
    feedid = query.split(' ', 1)[-1].strip()
    user = __get_user(update)
    feed = Feed.objects(user=user, feedid=feedid)
    if feed is None:
        message = u"Подписка не найдена"
    else:
        feed.delete()
        message = u"Подписка %s отменена" % (feedid)
    update.message.reply_text(message)

def do_test(bot, update):
    query = update['message']['text']
    user = __get_user(update)
    parts = query.split(' ')[1:]
    if len(parts) == 1:
        url = parts[0]
        feedtype = 'rss'
    else:
        message = u'Должен быть передан 1 параметр'
        update.message.reply_text(message)
        return
    user = __get_user(update)
    message = str(__verify_feed(url, update))
    update.message.reply_text(message)


def do_list(bot, update):
    query = update['message']['text']
    url = query.split(' ', 1)[-1].strip()
    user = __get_user(update)
    channels = Channel.objects(user=user)
    message = ""
    message = "У Вас всего каналов: %d" % (len(channels))
    update.message.reply_text(message)
    for ch in channels:
        message = ""
        feeds = Feed.objects(channel=ch)
        nfeeds = len(feeds)
        message += "\n Канал %s: %s, %d подписок" % (ch.chid, ch.name, nfeeds)
        for feed in feeds:
            message += "\n -- %s: %s : %s" % (feed.feedid, __get_feed_type(feed.feedtype), feed.url)
        update.message.reply_text(message)

def do_set(bot, update):
    query = update['message']['text']
    parts = query.split(' ', 1)[-1].strip()
    user = __get_user(update)
    if len(parts) == 4:
        cmdname, chid = opt, value = parts
        channel = Channel.objects.get(user=user, chid=chid)
        if opt == 'mode':
            if value == 'digest':
                val = FEED_MODE_DIGEST
            elif value == 'full':
                val = FEED_MODE_FULL
            else:
                return
            for f in Feed.objects(channel=channel):
                f.feedmode = val
                f.save()
            message = u'Настройки канала обновлены'
            update.message.reply_text(message)


def do_update(bot, update):
    user = __get_user(update)
    bot_logdebug(update, 'Запуск сбора новостей')
    os.system('%s news2rsscmd.py collect %s' % (PYTHON_EXEC, user.userid))
    bot_logdebug(update, 'Запуск отправки новостей по каналам')
    os.system('%s news2rsscmd.py digest %s' % (PYTHON_EXEC, user.userid))
    bot_logdebug(update, 'Новости разосланы по каналам')
    message = 'Все подписки обновлены'
    update.message.reply_text(message)


def start():
    connect('feedrebot', host='127.0.0.1', port=27017)

    updater = Updater(open(BOT_KEY, 'r').read())
    updater.dispatcher.add_handler(CommandHandler('help', helpcmd))
    updater.dispatcher.add_handler(CommandHandler('start', helpcmd))
    updater.dispatcher.add_handler(CommandHandler('test', do_test))
    updater.dispatcher.add_handler(CommandHandler('set', do_set))
    updater.dispatcher.add_handler(CommandHandler('channel', do_addchannel))
    updater.dispatcher.add_handler(CommandHandler('leave', do_leave))
    updater.dispatcher.add_handler(CommandHandler('list', do_list))
    updater.dispatcher.add_handler(CommandHandler('add', do_add))
    updater.dispatcher.add_handler(CommandHandler('remove', do_remove))
    updater.dispatcher.add_handler(CommandHandler('update', do_update))

    # log all errors
    updater.start_polling()
    updater.idle()



if __name__ == "__main__":
    start()
