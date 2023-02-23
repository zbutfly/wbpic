import os, wb.context as context
from wb.context import opts, getjson
from wb.utils import *

def checkjson(api, retry=3):
	log('DEBUG', 'weibo api {} parsing...', api)
	retried = 0
	while retried < retry:
		r = getjson(api)
		if r and 1 == r['ok']: 
			if retried > 0: log('INFO', 'api fetching success after {} retries')
			return r['data']
		retried += 1
		# log('WARN', '{} retry #{} result not ok: \n\t{}', api, retried, r)
		time.sleep(abs(random.gauss(3, 1)))
	if retried >= retry:
		log('ERROR', '{} fetch or parse failed after retries fully.', api)
		return

def checkprofile(userid, retry = 3):
	retried = 0
	profileurl = context.URL_WB_PROFILE.format(userid)
	while retried < retry:
		r = getjson(profileurl)
		if r and 1 == r['ok']: return r['data']['user']
		elif 'error' in r and r['error'] == '20003':
			log('INFO', 'user {} had died-_-'.format(userid))
			return
		retried += 1
		log('WARN', '{} retry #{} result not ok: \n\t{}', profileurl, retried, r)
		time.sleep(abs(random.gauss(3, 1)))
	if retried >= retry:
		log('ERROR', '{} fetch or parse failed after retries fully.', profileurl)
		return

minw = opts.get('min_dimension', 360)
minh = opts.get('min_dimension', 360)
notsmall = lambda w, h: w < minw or h <= minh or w + h < 1600

def listpics(pics, dirname, created, bid):
	count = 0
	for pi in range(0, len(pics)):
		try:
			pic = pics[pi]
		except:
			try:
				pic = pics[str(pi)]
			except:
				log('WARN', '{}/{}-{}-{} is live video, ignored {}', dirname, created.strftime('%Y%m%d_%H%M%S'), bid, pi, pic['large']['url'])
				continue

		ext = os.path.splitext(pic['large']['url'])[1].split('?')[0]
		zzx = pic['large']['url'].startswith('https://zzx.')
		if (zzx): ext = '[zzx]' + ext
		filename = created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(bid, pi, pic['pid'], ext)
		if ext.lower() == '.gif':
			log('WARN', '{}/{} is is gif, ignored {}', dirname, filename, pic['large']['url'])
			# log('WARN', '{}/{}[{}] at {} is gif, ignored {}', dirname, bid, pi, created, pic['large']['url'])
			continue
		img = {
			'id': pic['pid'],
			'url': pic['large']['url'],
			'width': int(pic['large']['geo']['width']),
			'height': int(pic['large']['geo']['height']),
			'dirname': dirname,
			'filename': filename
		}
		if notsmall(img['width'], img['height']):
			log('WARN', '{}/{} dimension {}:{} too small and ignored {}', dirname, filename, img['width'], img['height'], pic['large']['url'])
			continue
		if pic['pid'] in context.checkpids:
			log('DEBUG', 'ignore checked: {}\{} ', dirname, filename)
			continue
		dirn = context.basedir + os.sep + dirname
		if not os.path.isdir(dirn):
			os.makedirs(dirn, exist_ok=True)
		# TODO
		fetcher = Fetcher(img['url'], dirn + os.sep + filename, created, opts['headers_pics'], zzx)
		fetcher.start(ignoring=lambda s: s < 10240 or (not zzx and s < 51200))
		# print(context.CURL_CMD.format(img['url'], dirn + os.sep + filename))
		count += 1
		if context.checklogf: context.checklogf.writelines([pic['pid'], '\n'])
	return count

def parsepics(mblog):
	if mblog['pic_num'] <= 9: 
		pics = mblog['pics']
	else:
		datamore = checkjson(context.URL_WB_ITEM.format(mblog['bid']))
		pics = (datamore if datamore else mblog)['pics']
	if 'edit_count' in mblog and mblog['edit_count'] > 0: # find all history
		data = checkjson(context.URL_WB_ITEM_HIS.format(mblog['mid']))
		groups = [c['card_group'] for c in data['cards'] if c['card_type'] == 11]
		his = [c['mblog']['pics'] for cs in groups for c in cs if c['card_type'] == 9 and 'pics' in c['mblog']]
		pichis = [p for ps in his for p in ps]
		for p in [p for p in pichis if not p['pid'] in [pp['pid'] for pp in pics]]:
			pics += [p]
	return pics

def list(userid, after, progress, *, dir=None): # defalt yesterday to now
	count = 0
	since_id = ''
	if not dir: dir = dirname(checkprofile(userid))
	log('INFO', '[{}] user dowloading to {} is starting...'.format(progress, dir))
	while (True):
		data = checkjson(context.URL_WB_LIST.format(userid, since_id))
		if not data: 
			log('WARN', '{} fetched but no data, {} pictures found.', dirname, count)
			return count
		for card in data['cards']:
			if not 'mblog' in card or card['card_type'] != 9:
				continue
			mblog = card['mblog']
			if not 'pics' in mblog:
				continue

			created = parseTime(mblog['created_at'])
			if created.date() < after:
				log('INFO' if count > 0 else 'DEBUG', '[{}] {} exceed on {}, {} pictures found.',  progress, dirname, created.date(), count)
				return count
			count += listpics(parsepics(mblog), dirname, created, mblog['bid'])

		data = data['cardlistInfo']
		if not 'since_id' in data:
			log('INFO' if count > 0 else 'DEBUG', '[{}]{} finished whole weibo history, {} pictures found.', progress, dirname, count)
			return count
		since_id = data['since_id']

def list1(bid):
	url = context.URL_WB_ITEM.format(bid)
	data = checkjson(url)
	if not data or not 'pics' in data: 
		log('WARN', '{} fetched {} but no data.', dirname, url)
		return 0
	dir = dirname(data['user'])
	pics = data['pics']
	mid = data['mid']
	created = parseTime(data['created_at'])
	count = listpics(pics, dir, created, bid)
	log('INFO', '{} fetched, {} pictures found {}\n\thttps://weibo.com/{}/{}\n\thttps://weibo.com/detail/{}.', dirname, count, url, data['user']['id'], bid, mid)
	return count

def follows(): # defalt yesterday to now
	count_fo = 0
	page = 1
	fos = []
	try:
		while (True):
			data = checkjson(context.URL_FOLLOWERS.format(page))
			if not data: return fos
			count_fo = 0
			for cards in data['cards']:
				if not 'card_group' in cards: continue
				for card in cards['card_group']:
					if card['card_type'] != 10:
						continue
					# 2310930026_1_ _2253751997[15:]
					fos += [{card['user']['id']:  card['user']['screen_name']}]
					count_fo += 1
			log('DEBUG', '......{} followers found', count_fo)
			page = data['cardlistInfo']['page']
			if not page: return fos
	finally:
		log('INFO', 'Whole follows scanned and {} found.', len(fos))