import datetime, time, calendar, random, multiprocessing.dummy as mproc, pyjson5
from wb.utils import log, sigign
from fetcher import Fetcher
from wb.context import opts


class CONSTANTS(object):
	_HTTP_SLEEP_SECS = opts.get('interval', 0.4)
	_HTTP_RETRY_MAX = opts.get('retry', 3)
	_HTTP_HEADERS_AUTH = opts.get('headers_auth')
	_HTTP_HEADER_PICS = opts.get('headers_pics')

	_BASEDIR = opts['basedir'] if 'basedir' in opts else "wbpics"
	_MONS = list(calendar.month_abbr)


class Weibo(object):
	URL_WB_PROFILE = 'https://m.weibo.cn/profile/info?uid={}'
	URL_WB_LIST = 'https://m.weibo.cn/api/container/getIndex?containerid=230413{}_-_WEIBO_SECOND_PROFILE_WEIBO_ORI&since_id={}'
	# https://m.weibo.cn/detail/4850366267002849 or https://m.weibo.cn/status/{}
	# https://m.weibo.cn/statuses/show?id={mblog[bid]}	MtjjJhg2n JSON
	URL_WB_ITEM = 'https://m.weibo.cn/statuses/show?id={}'
	URL_WB_ITEM_HIS = 'https://m.weibo.cn/api/container/getIndex?containerid=231440_-_{}'
	URL_FOLLOWERS = 'https://m.weibo.cn/api/container/getIndex?containerid=231093_-_selffollowed&page={}'

	# created_at: "Sun Dec 25 00:54:56 +0800 2022"
	@classmethod
	def parseTime(createdStr: str):
		# datetime.strptime(createdStr, '%a %b %d %H:%M:%s %z %Y')
		segs = createdStr.split(' ')
		ts = segs[3].split(':')
		return datetime.datetime(int(segs[5]), CONSTANTS._MONS.index(segs[1]), int(segs[2]), int(ts[0]), int(ts[1]), int(ts[2]))

	@classmethod
	def getjson(url):
		response = Fetcher.gethttp(url, CONSTANTS._HTTP_HEADERS_AUTH, CONSTANTS._HTTP_SLEEP_SECS, CONSTANTS._HTTP_RETRY_MAX)
		try:
			result = pyjson5.loads(response)
			if result:
				return result
			log('ERROR', 'json invalid: {}\n{}', url, response)
		except Exception as e:
			log('ERROR', '{} json parse failed:\n{}', url, response)

	@classmethod
	def checkjson(api, retry=CONSTANTS._HTTP_RETRY_MAX):
		log('DEBUG', 'weibo api {} parsing...', api)
		retried = 0
		while retried < retry:
			r = Weibo.getjson(api)
			if r and 1 == r['ok']:
				if retried > 0:
					log('INFO', 'api {} fetching success after {}/{} retries', api, retried, retry)
				return r['data']
			retried += 1
			# log('WARN', '{} retry #{} result not ok: \n\t{}', api, retried, r)
			time.sleep(abs(random.gauss(3, 1)))
		if retried >= retry:
			log('ERROR', '{} fetch or parse failed after retries {} fully.', api, retry)
			return

	def __init__(self, parals: int = 1) -> None:
		self.parals = parals

	def parse(self):
		pass

	def _exec(self, args):
		return args[0](*(args[1:]))

	def poolize(self, args):
		c = 0
		if self.parals <= 1:
			for r in args:
				c += self._exec(r)
			return c
		with mproc.Pool(self.parals, sigign if 'cpu_count' in dir(mproc) else None) as p:
			try:
				for r in p.imap_unordered(self._exec, args):
					c += r
				return c
			except KeyboardInterrupt:
				p.terminate()
