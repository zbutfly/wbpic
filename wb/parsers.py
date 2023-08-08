import os, wb.context as ctx
from abc import ABCMeta, abstractmethod
from wb.utils import *
from wb.utils import _c, _LEVEL_COLORS
from wb.context import opts, getjson

class Parser(metaclass=ABCMeta):
# private
	@abstractmethod
	def listmblog(self, pics, dir, created, bid, filter=ctx.filter_small):
		pass
	@abstractmethod
	def listmblogbid(self, mid, dir = None):
		pass
# private
	@abstractmethod
	def listuserpage(self, userid, after, since_id, progress, dir, count_pics):
		pass
	@abstractmethod
	def listuser(self, userid, after, progress, dir=None): # defalt yesterday to now
		pass

# private
	def checkjson(self, api, retry=3, unembed = False):
		log('DEBUG', 'weibo api {} parsing...', api)
	# retried = 0
	# while retried < retry:
		r = getjson(api)
		if r and 1 == r['ok']: return r if unembed else r['data']
			# if retried > 0: log('INFO', 'api {} fetching success at {}th retrying of total {}', api, retried+1, retry)
		else: log('ERROR', 'Error [{}] for json api [{}], message {}', r['error_code'], api, r['message'] if 'message' in r else 'none')
		# retried += 1
		# log('WARN', '{} retry #{} result not ok: \n\t{}', api, retried, r)
		time.sleep(abs(random.gauss(1, 0.4)))
	# if retried >= retry:
	# 	log('ERROR', '{} fetch or parse failed after retries {} fully.', api, retry)
	# 	return

	def checkprofile(self, userid, retry = 3):
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
# private
	def toosmall(self, w, h): return w < Parser.minw or h <= Parser.minh or w + h < 1200

# private
	def parsepics(self, mblog):
		pics = mblog['pics']
		if (mblog['pic_num'] > 9 and len(pics) < mblog['pic_num']):
			datamore = self.checkjson(ctx.URL_WB_ITEM.format(mblog['bid']))
			pics = (datamore if datamore else mblog)['pics']
		if 'edit_count' in mblog and mblog['edit_count'] > 0: # find all history
			pids = set([p['pid'] for p in pics])
			data = self.checkjson(ctx.URL_WB_ITEM_HIS.format(mblog['mid']))
			pichis = [p for ps in [
					c['mblog']['pics'] for cs in [c['card_group'] for c in data['cards'] if c['card_type'] == 11]
					for c in cs if c['card_type'] == 9 and 'pics' in c['mblog'] and c['mblog']['pics'] != None and int(c['mblog']['id']) > 0
				]
				for p in ps]
			for p in [p for p in pichis if not p['pid'] in pids]:
				pids.add(p['pid'])
				pics.append(p)
		return pics

# private
	def listmblog0(self, img, filter, created, ext, zzx):
		# if ext.lower() != '.gif':
		# 	log('DEBUG', '{}/{} is is gif, ignored {}', dir, filename, url)
		# 	# log('DEBUG', '{}/{}[{}] at {} is gif, ignored {}', dir, bid, pi, created, url)
		# 	continue
		if filter and ext.lower() != '.gif' and self.toosmall(img['width'], img['height']):
			log('DEBUG', '{}/{} dimension {}:{} too small and ignored {}', dir, img['filename'], img['width'], img['height'], img['url'])
			return 0
		# if pic['pid'] in ctx.checkpids:
		# 	log('DEBUG', 'ignore checked: {}\{} ', dir, filename)
		# 	continue
		dirn = ctx.basedir + ctx.DOWN_MODE + os.sep + img['dirname']
		if not os.path.exists(dirn) or not os.path.isdir(dirn):
			try:
				os.makedirs(dirn, exist_ok=True)
			except:
				pass
		fetcher = Fetcher(img['url'], dirn + os.sep + img['filename'], created, opts['headers_pics'], zzx, ignoring=lambda s: filter and (s < 10240 or (not zzx and s < 20480)))
		bytes = fetcher.start()
		ctx.sum_bytes += bytes
		ctx.sum_pics += 1
		if (bytes > 0): ctx.sum_pics_downloaded += 1
		return 1

	def follows(self): # defalt yesterday to now
		count_fo = 0
		page = 1
		fos = []
		try:
			while (True):
				data = self.checkjson(ctx.URL_FOLLOWERS.format(page))
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

class WebParser(Parser):
	def listmblog(self, pics, dir, created, bid, filter=ctx.filter_small):
		count = 0
		for pi in pics:
			pic = pics[pi]
			url = pic['largest']['url']
			ext = os.path.splitext(re.sub('\?.*', '', url))[1]
			zzx = url.startswith('http://zzx.') or url.startswith('https://zzx.')
			# if (zzx): ext = '[zzx]' + ext
				# url = url.replace('/largeb/', '/large/')
			filename = created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(bid, count, pic['pic_id'], ext)
			count += self.listmblog0({
				'id': pic['pic_id'],
				'url': url,
				'width': int(pic['largest']['width']),
				'height': int(pic['largest']['height']),
				'dirname': dir,
				'filename': filename
			}, filter, created, ext, zzx)
		return count

	def listmblogbid(self, mid, dir = None):
		url = ctx.URL_WB_ITEM2.format(mid)
		data = self.checkjson(url, unembed = True)
		if not data or not 'pic_infos' in data:
			log('WARN', '{} fetched {} but no data.', dir, url)
			return 0
		bid = data['mblogid']
		if dir == None: dir = dirname(data['user'])
		pics = data['pic_infos'] # data['pics']
		mid = data['id']
		created = parseTime(data['created_at'])
		count = self.listmblog(pics, dir, created, bid, filter=False)
		log('INFO', '{} fetched, {} pictures found {}\n\thttps://weibo.com/{}/{}\n\thttps://weibo.com/detail/{}.', dir, count, url, data['user']['id'], mid, mid)
		return count

	now = -1
	def listuserpage(self, userid, after, pagenum, progress, dir, count_pics):
		if pagenum == 1 and ctx.DOWN_MODE == '_u': log('INFO', '[{}/page:0] start.', userid)
		if (WebParser.now > 0 and timer() - WebParser.now < 0.5): time.sleep(abs(random.gauss(0.5, 0.2))) # too fast, sleep
		data = super().checkjson(ctx.URL_WB_ALL.format(userid, pagenum))
		WebParser.now = timer()
		if not data:
			log('WARN', '{} fetched but no data, {} pictures found.', dir, count_pics)
			return 0, count_pics
		cards = data['list']
		count_orig = len(cards)
		if len(cards) == 0: return 0, count_pics # finished allover

		for c in cards: c['_createdat'] = parseTime(c['created_at'])
		if len(cards) > 1: cards.sort(reverse=True, key = lambda c: c['_createdat'].date())
		earliest = None
		for i in range(len(cards)-1, -1, -1):
			if not 'isTop' in cards[i] or cards[i]['isTop'] == 0:
				earliest = cards[i]['_createdat']
				break
		exceed = earliest == None or earliest.date() < after # last of page exceed
		cards = list(filter(lambda c:
				c['user']['id'] == int(userid) and not 'retweeted_status' in c and 'pic_infos' in c and c['_createdat'].date() >= after, cards))
		count_filtered = len(cards)
		if len(cards) > 0:
			for card in cards:
				if not dir:
					dir = dirname(card['user'])
					if dir: log('DEBUG', '{} user dowloading to {} is starting...'.format(progress, dir))
				curr_pics = self.listmblog(card['pic_infos'], dir, card['_createdat'], card['mblogid'])
				if ctx.DOWN_MODE == '_u': log('DEBUG', '[{}/{}: {} ], {} pictures found.', userid, card['_createdat'].strftime('%Y%m%d_%H%M%S'), card['mblogid'], curr_pics)
				count_pics += curr_pics
			if ctx.DOWN_MODE == '_u': log('INFO', '[{}, page#{}, {}], {} posts & {} /w pic, total {} pictures found.', 
				 userid, pagenum, earliest if None != earliest else 'unknown', count_pics, count_filtered, count_pics)
		if exceed: log('WARN' if count_pics > 0 else 'INFO', '{} Exceed {} on {} [page {}], {} pictures found',
						progress, _c(_LEVEL_COLORS['TODO'], dir if dir != None else userid),
						_c(_LEVEL_COLORS['WARN'], 'None') if earliest == None
							else _c(_LEVEL_COLORS['TODO'], earliest.date()) if count_pics > 0
							else earliest.date(), pagenum,
						_c(_LEVEL_COLORS['TODO'], count_pics) if count_pics > 0 else count_pics)
			#if 'isTop' in card and card['isTop'] > 0: continue
		return 0 if exceed else pagenum + 1, count_pics

	def listuser(self, userid, after, progress, dir=None): # defalt yesterday to now
		if dir: log('DEBUG', '{} Parsing "{}" uid [{}]'.format(progress, _c(_LEVEL_COLORS['TODO'], dir), userid))

		count_pics = 0
		pageno = 1
		while (pageno > 0):
			pageno, count_pics = self.listuserpage(userid, after, pageno, progress, dir, count_pics)
		return count_pics

# special parsing for wap
class WapParser(Parser):
	def listmblog(self, pics, dir, created, bid, filter=ctx.filter_small):
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
			ext = os.path.splitext(re.sub('\?.*', '', url))[1]
			zzx = url.startswith('http://zzx.') or url.startswith('https://zzx.')
			if (zzx): ext = '[zzx]' + ext
				#url = url.replace('/largeb/', '/large/').replace('https://', 'http://') + '&referer=weibo.com'
			filename = created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(bid, pi, pic['pid'], ext)
			count += self.listmblog0({
				'id': pic['pid'],
				'url': url,
				'width': int(pic['large']['geo']['width']),
				'height': int(pic['large']['geo']['height']),
				'dirname': dir,
				'filename': filename
			}, filter, created, ext, zzx)
		return count

	def listmblogbid(self, mid, dir = None):
		url = ctx.URL_WB_ITEM.format(mid)
		data = self.checkjson(url)
		if not data or not 'pics' in data:
			log('WARN', '{} fetched {} but no data.', dir, url)
			return 0
		bid = data['bid']
		if dir == None: dir = dirname(data['user'])
		pics = self.parsepics(data) # data['pics']
		mid = data['mid']
		created = parseTime(data['created_at'])
		count = self.listmblog(pics, dir, created, bid, filter=False)
		log('INFO', '{} fetched, {} pictures found {}\n\thttps://weibo.com/{}/{}\n\thttps://weibo.com/detail/{}.', dir, count, url, data['user']['id'], mid, mid)
		return count

	def listuserpage(self, userid, after, since_id, progress, dir, count_pics):
		data = self.checkjson(ctx.URL_WB_LIST.format(userid, since_id))
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
			count_pics += self.listmblog(self.parsepics(mblog), dir, created, mblog['bid'])
		data = data['cardlistInfo']
		if not 'since_id' in data:
			log('INFO' if count_pics > 0 else 'DEBUG', '{} {} finished whole weibo history, {} pictures found.', progress, dir, count_pics)
			return None, count_pics
		return data['since_id'], count_pics

	def listuser(self, userid, after, progress, dir=None): # defalt yesterday to now
		if dir: log('INFO', '{} Parsing "{}" uid [{}]'.format(progress, dir, userid))

		count_pics = 0
		since_id = ''
		while (since_id != None):
			since_id, count_pics = self.listuserpage(userid, after, since_id, progress, dir, count_pics)
		return count_pics	