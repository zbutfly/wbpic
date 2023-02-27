import os
from wb.models.statistics import Statistic
from wb.fetcher import Fetcher
from wb.utils import log
from wb.utils import log
from wb.models import Weibo, CONSTANTS
from wb.models.user import User
from wb.models.picture import Picture


class Mblog(Weibo):

	def __init__(self, user: User, json: dict) -> None:
		user.dircalc(json['user']['screen_name'])
		self.user = user
		self.bid = json['bid']
		self.mid = json['mid']
		self.created = Weibo.parseTime(json['created_at'])

		self.pic_num = json['pic_num']
		self.edit_count = json.get('edit_count', 0)
		self.pics = self.parsepics(json)
		super().__init__()

	def parsepic(self, pic, index: int) -> Statistic:
		url = pic['large']['url']
		ext = os.path.splitext(url)[1].split('?')[0]
		zzx = url.startswith('https://zzx.')
		if (zzx):
			ext = '[zzx]' + ext
		# url = url.replace('/largeb/', '/large/')
		filename = self.created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(self.bid, index, pic['pid'], ext)
		if ext.lower() == '.gif':
			log('DEBUG', '{}/{} is is gif, ignored {}', self.user.dirname, filename, url)
			return
			# log('DEBUG', '{}/{}[{}] at {} is gif, ignored {}', self.user.dirname, bid, index, created, url)
		img = {
		    'id': pic['pid'],
		    'url': url,
		    'width': int(pic['large']['geo']['width']),
		    'height': int(pic['large']['geo']['height']),
		    'dirname': self.user.dirname,
		    'filename': filename
		}
		if Picture.notsmall(img['width'], img['height']):
			log('DEBUG', '{}/{} dimension {}:{} too small and ignored {}', self.user.dirname, filename, img['width'], img['height'],
			    pic['large']['url'])
			return
		# if pic['pid'] in ctx.checkpids:
		# 	log('DEBUG', 'ignore checked: {}\{} ', self.user.dirname, filename)
		# 	continue
		dirn = CONSTANTS._BASEDIR + os.sep + self.user.dirname
		if not os.path.isdir(dirn):
			os.makedirs(dirn, exist_ok=True)
		return Fetcher(img['url'], dirn + os.sep + filename, self.created, CONSTANTS._HTTP_HEADER_PICS, zzx, lambda s: s < 10240 or
		               (not zzx and s < 51200)).start()

	def parsepics(self, json: dict) -> list['Picture']:
		if self.pic_num <= 9:
			pics = self.pics
		else:
			picmore = Weibo.checkjson(CONSTANTS.URL_WB_ITEM.format(self.bid))
			pics = (picmore if picmore else self).pics
		if self.edit_count > 0:  # find all history
			data = Weibo.checkjson(CONSTANTS.URL_WB_ITEM_HIS.format(self.mid))
			groups = [c['card_group'] for c in data['cards'] if c['card_type'] == 11]
			his = [c['mblog']['pics'] for cs in groups for c in cs if c['card_type'] == 9 and 'pics' in c['mblog']]
			pichis = [p for ps in his for p in ps]
			for p in [p for p in pichis if not p['pid'] in [pp['pid'] for pp in pics]]:
				pics.append(p)
		return pics

	def parse(self) -> Statistic:
		log('INFO', 'mblog {} to {} at {} parsing is starting on PROC {}...'.format(self.bid, self.user.dirname, self.created, os.getpid()))
		stat = Statistic(mblogs=1)
		for pi in range(0, len(self.pics)):
			try:
				pic = self.pics[pi]
			except:
				try:
					pic = self.pics[str(pi)]
				except:
					log('DEBUG', '{}/{}-{}-{} is live video, ignored {}', self.user.dirname, self.created.strftime('%Y%m%d_%H%M%S'), self.bid, pi,
					    pic['large']['url'])
					continue
			s = self.parsepic(pic, pi)
			if s:
				stat += s
			# print(ctx.CURL_CMD.format(img['url'], dirn + os.sep + filename))
			# if ctx.checklogf: ctx.checklogf.writelines([pic['pid'], '\n'])
		return stat

	@classmethod
	def listmblogbid(self, bid):
		url = Weibo.URL_WB_ITEM.format(bid)
		data = Weibo.checkjson(url)
		if not data or not 'pics' in data:
			log('WARN', '{} fetched {} but no data.', dir, url)
			return 0
		ud = data['user']
		u: User = User(ud['id'], screen_name=ud['screen_name'])
		wb: Mblog = Mblog(u, data).parse()
		count = wb.parse()
		log('INFO', '{} fetched, {} pictures found {}\n\thttps://weibo.com/{}/{}\n\thttps://weibo.com/detail/{}.', dir, count, url, u.id, bid,
		    wb.mid)
		return count
