import os, wb.context as context
from wb.context import opts, getjson
from wb.utils import *

def checkjson(api, *, info=None):
	log('DEBUG', '{}weibo api {} parsing...', '[{}]'.format(info) if info else '', api)
	retried = 0
	while retried < 5:
		r = getjson(api)
		if r and 1 == r['ok']: return r['data']
		retried += 1
		log('WARN', '{} retry #{} result not ok: \n\t{}', api, retried, r)
		time.sleep(abs(random.gauss(3, 1)))
	if retried >= 5:
		log('ERROR', '{} fetch or parse failed after retries fully.', api)
		return

def listpics(pics, dirname, created, bid):
	count = 0
	for pi in range(0, len(pics)):
		try:
			pic = pics[pi]
		except:
			try:
				pic = pics[str(pi)]
			except:
				log('WARN', '{}/{}[{}] at {} is live video, ignored {}', dirname, bid, pi, created, pic['large']['url'])
				continue

		ext = os.path.splitext(pic['large']['url'])[1].split('?')[0]
		if ext.lower() == '.gif':
			log('WARN', '{}/{}[{}] at {} is gif, ignored {}', dirname, bid, pi, created, pic['large']['url'])
			continue
		zzx = pic['large']['url'].startswith('https://zzx.')
		if (zzx): ext = '[zzx]' + ext
		filename = created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(bid, pi, pic['pid'], ext)
		img = {
			'id': pic['pid'],
			'url': pic['large']['url'],
			'width': int(pic['large']['geo']['width']),
			'height': int(pic['large']['geo']['height']),
			'dirname': dirname,
			'filename': filename
		}
		if img['width'] <= opts.get('min_dimension', 360) or img['height'] <= opts.get('min_dimension', 360):
			log('WARN', '{}/{}[{}] at {} is too small, ignored {}', dirname, bid, pi, created, pic['large']['url'])
			continue
		if pic['pid'] in context.checkpids:
			log('DEBUG', 'ignore checked: {}\{} ', dirname, filename)
			continue
		dirn = opts['basedir'] + os.sep + dirname if ('basedir' in opts) else dirname
		if not os.path.isdir(dirn):
			os.makedirs(dirn, exist_ok=True)
		# TODO
		fetcher = Fetcher(img['url'], dirn + os.sep + filename, created, opts['headers_pics'], zzx)
		fetcher.start(ignoring=lambda s: s < 10240 or (not zzx and s < 51200))
		# print(context.CURL_CMD.format(img['url'], dirn + os.sep + filename))
		count += 1
		if context.checklogf: context.checklogf.writelines([pic['pid'], '\n'])
	return count

listed_users = 0
def list(userid, after, total): # defalt yesterday to now
	global listed_users
	listed_users+=1
	count = 0
	since_id = ''
	while (True):
		data = checkjson(context.URL_WB_LIST.format(userid, since_id), info='{}/{}'.format(listed_users, total))
		if not data: return count
		dirname = ''
		for card in data['cards']:
			if not 'mblog' in card or card['card_type'] != 9:
				continue
			mblog = card['mblog']
			if not 'pics' in mblog:
				continue
			newdir = normalizedir(mblog)
			if dirname == '': dirname = newdir
			elif dirname != newdir: log('WARN', 'diff user, existed {}, found {}', dirname, newdir)

			created = parseTime(mblog['created_at'])
			if created.date() < after:
				log('DEBUG', '{} exceed on {}, {} pictures found and should be curl',  dirname, created.date(), count)
				return count

			if mblog['pic_num'] <= 9: pics = mblog['pics']
			else:
				datamore = checkjson(context.URL_WB_ITEM.format(mblog['bid']))
				pics = (datamore if datamore else mblog)['pics']
			count += listpics(pics, dirname, created, mblog['bid'])
		data = data['cardlistInfo']
		if not 'since_id' in data:
			log('DEBUG', '{} finished whole weibo history.', dirname)
			return count
		since_id = data['since_id']

def listall():
	since = parsesince()
	sum = 0
	uids = parseuids()
	total = len(uids)
	for uid in uids:
		sum += list(uid, since, total)
	log('INFO', 'Whole parsing finished, {} pictures found as CURL cmd.', sum)
	

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