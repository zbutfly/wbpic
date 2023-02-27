import os, time, random, wb.context as ctx
from wb.context import opts, getjson
from wb.fetcher import Fetcher
from wb.utils import *


def listmblogbid(bid):
	url = ctx.URL_WB_ITEM.format(bid)
	data = checkjson(url)
	if not data or not 'pics' in data:
		log('WARN', '{} fetched {} but no data.', dir, url)
		return 0
	dir = dirname(data['user'])
	pics = data['pics']
	mid = data['mid']
	created = parseTime(data['created_at'])
	count = listmblog(pics, dir, created, bid)
	log('INFO', '{} fetched, {} pictures found {}\n\thttps://weibo.com/{}/{}\n\thttps://weibo.com/detail/{}.', dir, count, url,
	    data['user']['id'], bid, mid)
	return count


def follows():  # defalt yesterday to now
	count_fo = 0
	page = 1
	fos = []
	try:
		while (True):
			data = checkjson(ctx.URL_FOLLOWERS.format(page))
			if not data:
				return fos
			count_fo = 0
			for cards in data['cards']:
				if not 'card_group' in cards:
					continue
				for card in cards['card_group']:
					if card['card_type'] != 10:
						continue
					# 2310930026_1_ _2253751997[15:]
					fos.append({card['user']['id']: card['user']['screen_name']})
					count_fo += 1
			log('DEBUG', '......{} followers found', count_fo)
			page = data['cardlistInfo']['page']
			if not page:
				return fos
	finally:
		log('INFO', 'Whole follows scanned and {} found.', len(fos))