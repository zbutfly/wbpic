import os, wb.context as ctx
from wb.context import opts, getjson
from wb.utils import *

def checkjson(api, retry=3):
	log('DEBUG', 'weibo api {} parsing...', api)
	retried = 0
	while retried < retry:
		r = getjson(api)
		if r and 1 == r['ok']:
			if retried > 0: log('INFO', 'api {} fetching success after {}/{} retries', api, retried, retry)
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
notsmall = lambda w, h: w < minw or h <= minh or w + h < 1600

def parsepics(mblog):
	if mblog['pic_num'] <= 9:
		pics = mblog['pics']
	else:
		datamore = checkjson(ctx.URL_WB_ITEM.format(mblog['bid']))
		pics = (datamore if datamore else mblog)['pics']
	if 'edit_count' in mblog and mblog['edit_count'] > 0: # find all history
		data = checkjson(ctx.URL_WB_ITEM_HIS.format(mblog['mid']))
		groups = [c['card_group'] for c in data['cards'] if c['card_type'] == 11]
		his = [c['mblog']['pics'] for cs in groups for c in cs if c['card_type'] == 9 and 'pics' in c['mblog']]
		pichis = [p for ps in his for p in ps]
		for p in [p for p in pichis if not p['pid'] in [pp['pid'] for pp in pics]]:
			pics.append(p)
	return pics

def listmblog(pics, dir, created, bid):
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
		if ext.lower() == '.gif':
			log('DEBUG', '{}/{} is is gif, ignored {}', dir, filename, url)
			# log('DEBUG', '{}/{}[{}] at {} is gif, ignored {}', dir, bid, pi, created, url)
			continue
		img = {
			'id': pic['pid'],
			'url': url,
			'width': int(pic['large']['geo']['width']),
			'height': int(pic['large']['geo']['height']),
			'dirname': dir,
			'filename': filename
		}
		if notsmall(img['width'], img['height']):
			log('DEBUG', '{}/{} dimension {}:{} too small and ignored {}', dir, filename, img['width'], img['height'], pic['large']['url'])
			continue
		# if pic['pid'] in ctx.checkpids:
		# 	log('DEBUG', 'ignore checked: {}\{} ', dir, filename)
		# 	continue
		dirn = ctx.basedir + os.sep + dir
		if not os.path.isdir(dirn):
			os.makedirs(dirn, exist_ok=True)
		ctx.sum_bytes += Fetcher(img['url'], dirn + os.sep + filename, created, opts['headers_pics'], zzx, lambda s: s < 10240 or (not zzx and s < 51200)).start()
		# print(ctx.CURL_CMD.format(img['url'], dirn + os.sep + filename))
		count += 1
		# if ctx.checklogf: ctx.checklogf.writelines([pic['pid'], '\n'])
	return count

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
	log('INFO', '{} fetched, {} pictures found {}\n\thttps://weibo.com/{}/{}\n\thttps://weibo.com/detail/{}.', dir, count, url, data['user']['id'], bid, mid)
	return count

def listuserpage(userid, after, since_id, progress, dir, mblog_args):
	data = checkjson(ctx.URL_WB_LIST.format(userid, since_id))
	if not data:
		log('WARN', '{} fetched but no data, {} pictures found.', dir, len(mblog_args))
		return None, mblog_args
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
			log('INFO' if len(mblog_args) > 0 else 'DEBUG', '{} {} exceed on {}, {} pictures found.',  progress, dir, created.date(), len(mblog_args))
			return None, mblog_args
		mblog_args.append((listmblog, parsepics(mblog), dir, created, mblog['bid']))
	data = data['cardlistInfo']
	if not 'since_id' in data:
		log('INFO' if len(mblog_args) > 0 else 'DEBUG', '{} {} finished whole weibo history, {} pictures found.', progress, dir, len(mblog_args))
		return None, mblog_args
	return data['since_id'], mblog_args

def listuser(userid, after, progress, dir=None): # defalt yesterday to now
	since_id = ''
	if dir: log('DEBUG', '{} user dowloading to {} is starting...'.format(progress, dir))
	mblog_args = []
	while (since_id != None):
		since_id, mblog_args = listuserpage(userid, after, since_id, progress, dir, mblog_args)
	if len(mblog_args) == 0: return 0
	return ctx.poolize(mblog_args, 1)

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