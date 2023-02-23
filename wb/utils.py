import sys, os, time, calendar, datetime, dateutil, math, random, re, pyjson5, requests, shutil, copy
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
	msg = '{} [{}] '.format(_c(fcolor.BLUE, 'REM'), _c(levcolor, level)) + _c(levcolor, format)
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
	if bytes == 0:
		return "0B"
	i = int(math.floor(math.log(bytes, 1024)))
	n = BYTE_NAMES[i]
	# p = math.pow(1024, i)
	s = roundreserve(bytes / n[1], 3)
	return "%s%s" % (s, n[0])


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
	for cats in [f.path for f in os.scandir(basedir) if f.is_dir() and (accepting(f.name) if accepting else True)]:
		for entry in [ff for ff in os.scandir(cats) if ff.is_dir()]:
			m = re.findall(r'#(\d{10})', entry.name) #, flags=re.DOTALL
			if m:
				for uid in m:
					if uid in uids: log('ERROR', 'duplicated userid {} tag in {} and {}', uid, entry.path, uids[uid])
					else: uids[uid] = entry.path.replace(basedir, '', 1) if entry.path.startswith(basedir) else entry.path
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
def httpget(target, headers, retry, interval):
	retried = 0
	while retried < retry:
		try:
			with session.get(target, headers = headers, stream = False, verify = False) as r:
				if r.status_code == 418 or r.status_code > 500: # retry only for spam or server-side error
					retried = retried + 1
					log('WARN', '{} retry #{}, result {}', target, retried, r)
					time.sleep(abs(random.gauss(interval*10, interval*4)))
					continue
				if r.status_code < 200 and r.status_code >= 300:
					log('ERROR', '{} fetch incorrectly return {}, {}', target, r, r.text)
					return
				return r.text
		except Exception as e: 
			log('ERROR', '{} failed {}', target, e) # ', result {}.\n{}', r, r.text 
			return 
		finally:
			time.sleep(abs(random.gauss(interval, interval/2.5)))
	log('ERROR', '{} failed after retries {}', target, retried)

class Fetcher(object):
	def __init__(self, url, file_path, created, headers, forcing):
		self.url = url
		self.file_path = file_path
		self.headers = copy.deepcopy(headers)
		self.created = created
		self.forcing = forcing

	def save(self, r, f, size_curr, size_total):
		for chunk in r.iter_content(chunk_size=1024):
			size_curr += len(chunk)
			f.write(chunk)
			f.flush()

			done = int(50 * size_curr / size_total)
			sys.stdout.write("\r[%s%s] %d%%" % ('█' * done, ' ' * (50 - done), 100 * size_curr / size_total))
			sys.stdout.flush()

	def remotetime(self, r):
		last_modified = r.headers.get('Last-Modified')
		return dateutil.parser.parse(last_modified) if last_modified else None

	def start(self, *, ignoring=None):
		try:
			with session.get(self.url, stream=True, headers=self.headers) as r:
				size_expected = int(r.headers['Content-Length'])
		except Exception as e:
			log('ERROR', '{} fetching failed {} for erro {}.', self.file_path, self.url, e)
			log('ERROR', '{} invalid {}, failed {}', self.file_path, r, self.url)
		if r.status_code < 200 or r.status_code > 299:
			log('ERROR', '{} invalid {}, failed {}', self.file_path, r, self.url)
			return
		if ignoring and ignoring(size_expected):
			log('WARN', '{} too small [{}], ignored {}', self.file_path, bsize(size_expected), self.url)
			return
		size_curr = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
		if size_curr > size_expected:
			log('WARN', '{} current size {} exceed expected {}, ignored {}', self.file_path, bsize(size_curr), bsize(size_expected), self.url)
			return	
		if size_curr == size_expected:
			log('TRACE', '{} existed and size {} match, ignore {}', self.file_path, bsize(size_curr), self.url)
			return
		size_needs = size_expected - size_curr if size_curr > 0 else -1
		try:
			while size_curr < size_expected:
				if size_curr == 0:
					log('DEBUG', "%s total %s fetching..." % (self.file_path, bsize(size_expected)))
				else:
					log('INFO', "%s total %s and existed %s, resuming from %2.2f%%..." % (self.file_path, bsize(size_expected), bsize(size_curr), 100 * size_curr / size_expected))

				if (size_curr > 0): self.headers['Range'] = 'bytes=%d-' % size_curr
				try:
					with session.get(self.url, stream=True, headers=self.headers) as r, open(self.file_path, "ab") as f:
						shutil.copyfileobj(r.raw, f)
				except Exception as e:
					log('ERROR', '{} fetching failed {} for error {}, \n\ttotal {} bytes and {} bytes fetched.', self.file_path, self.url, e, size_expected, size_curr)
				finally:
					size_curr = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
		finally:
			os.utime(self.file_path, (int(self.created.timestamp()), int(self.created.timestamp())))
			extra = 'total: {}'.format(bsize(size_expected), bsize(size_curr))
			if size_needs > 0 or size_curr != size_expected: 
				if size_needs > 0: extra += '/need: {}'.format(bsize(size_needs))
				if size_curr != size_expected: extra += '/current: {}'.format(bsize(size_curr))
				log('INFO', '{} fetching (resuming) finished from {}, {}', self.file_path, self.url, extra)	
			else: log('DEBUG', '{} fetching (whole) finished from {}, {}', self.file_path, self.url, extra)
