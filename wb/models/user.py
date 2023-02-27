import os, datetime, re
from wb.utils import log
from wb.models import Weibo, CONSTANTS as const
from wb.models.mblog import Mblog


class User(Weibo):

	def dircalc(self, *, screen_name: str = None, dirname: str = None):
		if screen_name:
			self.screen_name = screen_name
		if dirname:
			self.dirname = dirname
		if not self.dirname:
			if self.screen_name:
				nick = re.sub('^[·_-]+', '', self.screen_name)
				nick = re.sub('[·_-]+$', '', nick)
				self.dirname = '{}#{}'.format(nick, self.userid)
			else:
				self.dirname = '#' + self.userid
		if not self.screen_name:
			self.screen_name = self.dirname.split('#', 1)[0] if self.dirname and not self.dirname.startswith('#') else None
		log('DEBUG', '{} user dowloading to {} is starting...'.format(self.progress, dirname))

	def __init__(self,
	             userid,
	             *,
	             since: datetime.date = None,
	             dirname: str = None,
	             screen_name: str = None,
	             curr: int = 1,
	             total: int = 1) -> None:
		super().__init__()
		self.userid = int(userid)
		self.dircalc(dirname=dirname, screen_name=screen_name)
		self.since = since
		self.progress = '[{}/{}]'.format(curr, total)
		self.since_id: str = ""

	def parsepage(self, mblogs: list[Mblog]) -> list[Mblog]:
		data = Weibo.checkjson(Weibo.URL_WB_LIST.format(self.userid, self.since_id))
		if not data:
			log('WARN', '{} fetched but no data, {} pictures found.', self.dirname, len(mblogs))
			return mblogs
		for card in data['cards']:
			if not 'mblog' in card or card['card_type'] != 9:
				continue
			mblog = Mblog(self, card['mblog'])
			if not mblog.pics:
				continue
			if mblog.created.date() < self.since:
				self.since_id = None
				log('INFO' if len(mblogs) > 0 else 'DEBUG', '{} {} exceed on {}, {} pictures found.', self.progress, self.dirname,
				    mblog.created.date(), len(mblogs))
				return mblogs
			mblogs.append(mblog)
		data = data['cardlistInfo']
		self.since_id = data['cardlistInfo'].get('since_id')
		if self.since_id == '':
			self.since_id = None
		if self.since_id:
			log('INFO' if len(mblogs) > 0 else 'DEBUG', '{} {} finished whole weibo history, {} pictures found.', self.progress, self.dirname,
			    len(mblogs))
		return mblogs

	def parse(self):
		log('INFO', '{} user dowloading to {} is starting on PROC {}...'.format(self.progress, self.dirname, os.getpid()))
		mblogs = []
		while (self.since_id):
			mblogs = self.parsepage(mblogs)
		return self.poolize(mblogs) if len(mblogs) == 0 > 0 else 0
