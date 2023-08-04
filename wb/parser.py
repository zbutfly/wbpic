import os, wb.context as ctx
from wb.context import opts, getjson
from wb.utils import _c, _LEVEL_COLORS
from wb.utils import *

def checkjson(api, retry=3):
	log('DEBUG', 'weibo api {} parsing...', api)
	retried = 0
	while retried < retry:
		r = getjson(api)
		if r and 1 == r['ok']: 
			if retried > 0: log('INFO', 'api {} fetching success at {}th retrying of total {}', api, retried+1, retry)
			return r['data']
		retried += 1
		# log('WARN', '{} retry #{} result not ok: \n\t{}', api, retried, r)
		time.sleep(abs(random.gauss(3, 1)))
	if retried >= retry:
		log('ERROR', '{} fetch or parse failed after retries {} fully.', api, retry)
		return

def checkprofile(userid, retry = 3):
	retried = 0
	profileurl = ctx.URL_WB_PROFILE.format(userid)
	while retried < retry:
		r = getjson(profileurl)
		if r and 1 == r['ok']: return r['data']['user']
		elif 'errno' in r:
			match r['errno']:
				case '20003':
					log('INFO', 'user {} had died-_-'.format(userid))
					return
				case '100006':
					log('ERROR', 'api {} denied by auth-_-'.format(profileurl))
					return userid
		retried += 1
		log('WARN', '{} retry #{} result not ok: \n\t{}', profileurl, retried, r)
		time.sleep(abs(random.gauss(3, 1)))
	if retried >= retry:
		log('ERROR', '{} fetch or parse failed after retries fully.', profileurl)
		return

minw = opts.get('min_dimension', 360)
minh = opts.get('min_dimension', 360)
toosmall = lambda w, h: w < minw or h <= minh or w + h < 1200

def parsepics(mblog):
	pics = mblog['pics']
	if (mblog['pic_num'] > 9 and len(pics) < mblog['pic_num']):
		datamore = checkjson(ctx.URL_WB_ITEM.format(mblog['bid']))
		pics = (datamore if datamore else mblog)['pics']
	if 'edit_count' in mblog and mblog['edit_count'] > 0: # find all history
		pids = set([p['pid'] for p in pics])
		data = checkjson(ctx.URL_WB_ITEM_HIS.format(mblog['mid']))
		pichis = [p for ps in [
				c['mblog']['pics'] for cs in [c['card_group'] for c in data['cards'] if c['card_type'] == 11]
				for c in cs if c['card_type'] == 9 and 'pics' in c['mblog'] and c['mblog']['pics'] != None and int(c['mblog']['id']) > 0
			]
			for p in ps]
		for p in [p for p in pichis if not p['pid'] in pids]:
			pids.add(p['pid'])
			pics.append(p)
	return pics

def listmblog(pics, dir, created, bid, filter=ctx.filter_small):
	count = 0
	for pi in range(0, len(pics)):
		try:
			pic = pics[pi]
		except:
			try:
				pic = pics[str(pi)]
			except:
				log('DEBUG', '{}/{}-{}-{} is live video, ignored {}', dir, created.strftime('%Y%m%d_%H%M%S'), bid, pi, pic['large']['url'])
				continue

		url = pic['large']['url']
		ext = os.path.splitext(url)[1].split('?')[0]
		zzx = url.startswith('https://zzx.')
		if (zzx): 
			# url = url.replace('/largeb/', '/large/') 
			ext = '[zzx]' + ext
		filename = created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(bid, pi, pic['pid'], ext)
		# if ext.lower() != '.gif':
		# 	log('DEBUG', '{}/{} is is gif, ignored {}', dir, filename, url)
		# 	# log('DEBUG', '{}/{}[{}] at {} is gif, ignored {}', dir, bid, pi, created, url)
		# 	continue
		img = {
			'id': pic['pid'],
			'url': url,
			'width': int(pic['large']['geo']['width']),
			'height': int(pic['large']['geo']['height']),
			'dirname': dir,
			'filename': filename
		}
		if filter and ext.lower() != '.gif' and toosmall(img['width'], img['height']):
			log('DEBUG', '{}/{} dimension {}:{} too small and ignored {}', dir, filename, img['width'], img['height'], pic['large']['url'])
			continue
		# if pic['pid'] in ctx.checkpids:
		# 	log('DEBUG', 'ignore checked: {}\{} ', dir, filename)
		# 	continue
		dirn = ctx.basedir + os.sep + dir
		if not os.path.exists(dirn) or not os.path.isdir(dirn):
			try:
				os.makedirs(dirn, exist_ok=True)
			except:
				pass
		fetcher = Fetcher(img['url'], dirn + os.sep + filename, created, opts['headers_pics'], zzx, ignoring=lambda s: filter and (s < 10240 or (not zzx and s < 20480)))
		bytes = fetcher.start()
		ctx.sum_bytes += bytes
		ctx.sum_pics += 1
		if (bytes > 0): ctx.sum_pics_downloaded += 1
		# print(ctx.CURL_CMD.format(img['url'], dirn + os.sep + filename))
		count += 1
		# if ctx.checklogf: ctx.checklogf.writelines([pic['pid'], '\n'])
	return count

def listmblogbid(mid):
	url = ctx.URL_WB_ITEM.format(mid)
	data = checkjson(url)
	bid = data['bid']
	if not data or not 'pics' in data: 
		log('WARN', '{} fetched {} but no data.', dir, url)
		return 0
	dir = dirname(data['user'])
	pics = parsepics(data) # data['pics']
	mid = data['mid']
	created = parseTime(data['created_at'])
	count = listmblog(pics, dir, created, bid, filter=False)
	log('INFO', '{} fetched, {} pictures found {}\n\thttps://weibo.com/{}/{}\n\thttps://weibo.com/detail/{}.', dir, count, url, data['user']['id'], mid, mid)
	return count

def listuserpage(userid, after, since_id, progress, dir, count_pics):
	data = checkjson(ctx.URL_WB_LIST.format(userid, since_id))
	if not data: 
		log('WARN', '{} fetched but no data, {} pictures found.', dir, count_pics)
		return None, count_pics
	for card in data['cards']:
		if not 'mblog' in card or card['card_type'] != 9:
			continue
		mblog = card['mblog']
		if not 'pics' in mblog:
			continue
		if not dir: 
			dir = dirname(mblog['user'])
			if dir: log('DEBUG', '{} user dowloading to {} is starting...'.format(progress, dir))
		created = parseTime(mblog['created_at'])
		if created.date() < after:
			log('INFO' if count_pics > 0 else 'DEBUG', '{} Exceed {} on {}, {} pictures found',  progress, _c(_LEVEL_COLORS['TODO'], dir), created.date(), count_pics)
			return None, count_pics
		count_pics += listmblog(parsepics(mblog), dir, created, mblog['bid'])
	data = data['cardlistInfo']
	if not 'since_id' in data:
		log('INFO' if count_pics > 0 else 'DEBUG', '{} {} finished whole weibo history, {} pictures found.', progress, dir, count_pics)
		return None, count_pics
	return data['since_id'], count_pics

def listuser(userid, after, progress, dir=None): # defalt yesterday to now
	count_pics = 0
	since_id = ''
	if dir: log('INFO', '{} Parsing "{}" uid [{}]'.format(progress, dir, userid))
	while (since_id != None):
		since_id, count_pics = listuserpage(userid, after, since_id, progress, dir, count_pics)
	return count_pics

def follows(): # defalt yesterday to now
	count_fo = 0
	page = 1
	fos = []
	try:
		while (True):
			data = checkjson(ctx.URL_FOLLOWERS.format(page))
			if not data: return fos
			count_fo = 0
			for cards in data['cards']:
				if not 'card_group' in cards: continue
				for card in cards['card_group']:
					if card['card_type'] != 10:
						continue
					# 2310930026_1_ _2253751997[15:]
					fos.append({card['user']['id']:  card['user']['screen_name']})
					count_fo += 1
			log('DEBUG', '......{} followers found', count_fo)
			page = data['cardlistInfo']['page']
			if not page: return fos
	finally:
		log('INFO', 'Whole follows scanned and {} found.', len(fos))