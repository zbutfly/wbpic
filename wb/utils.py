import sys, os, time, calendar, datetime, dateutil, requests, math, random, re, pyjson5, shutil, copy
from timeit import default_timer as timer
from colorama import Fore as fcolor
# from hurry.filesize import bsize

WBPIC_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))

def _c(color, str):
	return '{}{}{}'.format(color, str, fcolor.RESET) if color else str

_LEVEL_COLORS = {
	'TODO': fcolor.MAGENTA,
	'TRACE': fcolor.BLUE,
	'DEBUG': fcolor.GREEN,
	'INFO': fcolor.CYAN,
	'WARN': fcolor.YELLOW,
	'ERROR': fcolor.RED
}

_LEVEL_GRADE = {
	'TODO': 99,
	'TRACE': -2,
	'DEBUG': -1,
	'INFO': 0,
	'WARN': 1,
	'ERROR': 2
}

_LOG_LEVEL = None
def loglevel(level):
	global _LOG_LEVEL
	_LOG_LEVEL = level.upper()

def log(level, format, *vars):
	if _LOG_LEVEL and _LEVEL_GRADE[level.upper()] < _LEVEL_GRADE[_LOG_LEVEL.upper()]:
		return
	level = level if level else 'INFO'
	levcolor = _LEVEL_COLORS[level.upper()]
	# if threadpool:
		# msg = '{} {} [{}] '.format(_c(fcolor.BLUE, 'REM'), threading.current_thread(), _c(levcolor, level)) + _c(levcolor, format)
	# else:
	prefix = _c(fcolor.BLUE, 'REM[{}]'.format(datetime.datetime.now().strftime("%H:%M:%S"))) # %m%d
	msg = '{} [{}] '.format(prefix, _c(levcolor, level)) + _c(levcolor, format)
	print(msg.format(*vars), file=sys.stderr)

BYTE_NAMES = (
	("B", 1),
	("KB", math.pow(1024, 1)),
	("MB", math.pow(1024, 2)),
	("GB", math.pow(1024, 3)),
	("TB", math.pow(1024, 4)),
	("PB", math.pow(1024, 5)),
	("EB", math.pow(1024, 6)),
	("ZB", math.pow(1024, 7)),
	("YB", math.pow(1024, 8))
)

def roundreserve(x, n):
	i = math.log10(x)
	r = round(x, -int(math.floor(i)) + (n - 1))
	return int(r) if i >= n - 1 else r
	# i = int(math.log10(x))
	# r = n - i
	# if x >= 1: r -= 1
	# r = math.pow(10, r)
	# r = round(x * r) / r
	# return int(r) if i >= n - 1 else r

def bsize(bytes):
	if bytes == 0: return "0B"
	if bytes < 0: return "-1"
	i = int(math.floor(math.log(bytes, 1024)))
	n = BYTE_NAMES[i]
	# p = math.pow(1024, i)
	s = roundreserve(bytes / n[1], 3)
	return "%s%s" % (s, n[0])

def msec(ms):
	return float('%.3g' % ms)

# created_at: "Sun Dec 25 00:54:56 +0800 2022"
_MONS = list(calendar.month_abbr)
def parseTime(createdStr):
	# datetime.strptime(createdStr, '%a %b %d %H:%M:%s %z %Y')
	segs = createdStr.split(' ')
	ts = segs[3].split(':')
	return datetime.datetime(int(segs[5]), _MONS.index(segs[1]), int(segs[2]), int(ts[0]), int(ts[1]), int(ts[2]))

def dirname(user):
	nick = user['screen_name']
	nick = re.sub('^[·_-]+', '', nick)
	nick = re.sub('[·_-]+$', '', nick)
	return '{}#{}'.format(nick, user['id'])

def parsesince():
	if len(sys.argv) <= 1:
		since = '1' # default yesterday
	elif sys.argv[1] != '':
		since = sys.argv[1]
	else:
		since = '20090801' # weibo init on 20090814
	if eval(since) < 9999: # days
		since = datetime.datetime.today().date() - datetime.timedelta(eval(since))
	else:
		since = datetime.datetime.strptime(since, '%Y%m%d').date()
	log('INFO', 'since: {}', since)
	return since

def parsedirs(basedir, accepting=None):
	uids = {}
	for cats in [f.path for f in os.scandir(basedir) if f.is_dir() and (not accepting or accepting(f.name))]:
		for entry in [ff for ff in os.scandir(cats) if ff.is_dir()]:
			m = re.findall(r'#(\d{10})', entry.name) #, flags=re.DOTALL
			if m:
				for uid in m:
					p = entry.path.replace(basedir, '', 1) if entry.path.startswith(basedir) else entry.path
					if uid in uids: log('ERROR', 'duplicated userid {} tag in {} (use this) and {}', uid, uids[uid], p)
					else: uids[uid] = p
	return uids

def parseuids(idsarg, accepting=None):
	if len(idsarg) > 0:
		if len(idsarg) == 1 and idsarg[0].startswith('@'):
			if not idsarg[0].endswith(os.sep):
				with open(idsarg[0][1:]) as f: return pyjson5.load(f)
			else:
				return parsedirs(idsarg[0][1:], accepting)
		else: return [eval(i) for i in idsarg]
	else:
		with open(WBPIC_DIR + os.sep + os.sep + 'wbpic-uids.json', encoding='UTF-8') as f: return pyjson5.load(f)

session = requests.Session()
session_static = requests.Session()

def httpget(target, headers, interval, retry):
	retried = 0
	now = timer()
	while retried < retry:
		try:
			with session.get(target, headers = headers, stream = False, verify = False) as r:
				spent = timer() - now
				if r.status_code == 418 or r.status_code > 500: # retry only for spam or server-side error
					retried = retried + 1
					log('WARN', '{} retry #{}, result {}', target, retried, r)
					time.sleep(abs(random.gauss(interval*10, interval*4)))
					continue
				if r.status_code < 200 and r.status_code >= 300:
					log('ERROR', '{} fetch incorrectly spent {} ms secs return {}, {}', target, msec(spent), r, r.text)
					return
				if (spent > 2): log('DEBUG' if spent < 5 else 'WARN', '{} fetch slow spent {} secs return {}', target, msec(spent), r)
				return r.text
		except Exception as e:
			log('ERROR', '{} spent {} secs and failed {}', target, msec(timer() - now), e)
			return
		finally:
			time.sleep(abs(random.gauss(interval, interval/2.5)))
	log('ERROR', '{} failed after retries {} and spent {} ms.', target, retried, msec(timer() - now))

class Fetcher(object):
	def __init__(self, url, file_path, created, headers, forcing, ignoring=None):
		self.url = url
		self.file_path = file_path
		self.headers = copy.deepcopy(headers)
		self.created = created
		self.forcing = forcing
		# self.auth_headers = auth_headers

		self.size_begin = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
		self.size_expected = -1 if self.forcing else self.sizeremote()
		self.size_needs = self.sizecheck(ignoring)

	def remotetime(self, r):
		last_modified = r.headers.get('Last-Modified')
		return dateutil.parser.parse(last_modified) if last_modified else None

	def sizeremote(self): # return size_expected
		if (self.url.startswith('http://zzx') or self.url.startswith('https://zzx')): return -1;
		retried = 0
		retries = 5
		sleep = 2
		sleepval = 0.7
		while retried < retries:
			if retried > 0: time.sleep(abs(random.gauss(sleep, sleepval)))
			try:
				with session_static.head(self.url, stream=True, headers=self.headers) as r:
					r.raise_for_status()
					if retried > 0: log('INFO', '[retry #{}]{} HEAD successed {}.', retried, self.file_path, self.url)
					return int(r.headers['Content-Length']) if 'Content-Length' in r.headers else -1
			except Exception as e:
				retried = retried + 1
				if (retried >= retries):
					log('ERROR', '[retry #{}]{} HEAD failed {} for error {}.', retried, self.file_path, self.url, e)
					return -1
		return -1

	def sizecheck(self, ignoring): # return size_needs for resume, 0 for match or exceed so no download, -1 for redownload
		if self.size_expected < 0: return -1
		if ignoring and ignoring(self.size_expected):
			log('DEBUG', '{} HEAD too small [{}], ignored {}', self.file_path, bsize(self.size_expected), self.url)
			return 0
		if self.size_begin > self.size_expected:
			log('WARN', '{} HEAD current size {} exceed expected {}, ignored {}', self.file_path, bsize(self.size_begin), bsize(self.size_expected), self.url)
			return 0
		if self.size_begin == self.size_expected:
			log('TRACE', '{} HEAD existed and size {} match, ignore {}', self.file_path, bsize(self.size_begin), self.url)
			return 0
		return self.size_expected - self.size_begin

	def sizelog(self, size_fetched, size_curr, spent):
		speed = size_fetched / spent # bytes/second
		extra = 'total: {}/fetched: {}'.format(bsize(self.size_expected), bsize(size_fetched))
		if self.size_expected < 0 or size_curr == self.size_expected:
			log('DEBUG' if speed == 0 or speed >= 50000 else 'INFO', '{} fetching entirely finished, speed {}/s spent {} secs from {}, {}', self.file_path, bsize(speed), msec(spent), self.url, extra)
		else:
			if self.size_needs > 0: extra += '/need: {}'.format(bsize(self.size_needs))
			extra += '/current: {}'.format(bsize(size_curr))
			log('INFO', '{} fetching (resuming) finished spent {} secs from {}, {}', self.file_path, msec(spent), self.url, extra)

	def download_directly(self, *, decode_unicode=False):
		size_expected = -1
		size_writen = 0
		with session_static.get(self.url, stream=True, headers=self.headers) as r:
			r.raise_for_status()
			if 'Content-Length' in r.headers: size_expected = int(r.headers['Content-Length'])
			size_writen = 0
			with open(self.file_path, 'w' if decode_unicode else 'wb') as f:
				for chunk in r.iter_content(decode_unicode = decode_unicode, chunk_size=9612):
					if chunk:
						size_writen += f.write(chunk) # chunk.decode("utf-8")
		if size_expected > 0 and size_writen != size_expected: log('ERROR', '{} size {} not match expected {} from {}', self.file_path, size_writen, size_expected, self.url)
		return size_writen

	def download(self, size_expected, size_curr):
		try:
			if (size_expected < 0): return self.download_directly()
				# zzx = self.download_directly()
				# self.url = self.url.replace('/largeb/', '/large/')
				# self.file_path = self.file_path.replace('[zzx]', '')
				# zzx0 = self.download_directly()
				# return zzx0 if zzx0 > 0 else zzx
			while size_curr < size_expected:
				if (size_expected >= 0):
					if size_curr == 0:
						log('DEBUG', "%s total %s to be fetched..." % (self.file_path, bsize(size_expected)))
					else:
						log('INFO', "%s total %s and existed %s, resuming from %2.2f%%..." % (self.file_path, bsize(size_expected), bsize(size_curr), 100 * size_curr / size_expected))
				if (size_curr > 0): self.headers['Range'] = 'bytes=%d-' % size_curr
				with session_static.get(self.url, stream=True, headers=self.headers) as r:
					r.raise_for_status()
					with open(self.file_path, "ab") as f:
						shutil.copyfileobj(r.raw, f)
				size_curr = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
		except Exception as e:
			log('ERROR', '{} fetching failed {} for error {}, \n\ttotal {} bytes and {} bytes fetched.', self.file_path, self.url, e, size_expected, size_curr)
		finally:
			if os.path.exists(self.file_path):
				os.utime(self.file_path, (int(self.created.timestamp()), int(self.created.timestamp())))
				return os.path.getsize(self.file_path)
			else: return 0

	def start(self):
		now = timer()
		if self.size_needs == 0: return 0
		size_curr = self.download(self.size_expected, self.size_begin)
		spent = timer() - now
		size_fetched = size_curr - self.size_begin
		self.sizelog(size_fetched, size_curr, spent)
		return size_fetched
