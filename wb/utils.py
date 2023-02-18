import sys, os, time, calendar, datetime, dateutil, random, re, pyjson5, requests, shutil, copy
from colorama import Fore as fcolor
from hurry.filesize import size

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

def log(level, format, *vars):
	level = level if level else 'INFO'
	levcolor = _LEVEL_COLORS.get(level.upper())
	msg = '{} [{}] '.format(_c(fcolor.BLUE, 'REM'), _c(levcolor, level)) + _c(levcolor, format)
	print(msg.format(*vars), file=sys.stderr)

# created_at: "Sun Dec 25 00:54:56 +0800 2022"
_MONS = list(calendar.month_abbr)
def parseTime(createdStr):
	# datetime.strptime(createdStr, '%a %b %d %H:%M:%s %z %Y')
	segs = createdStr.split(' ')
	ts = segs[3].split(':')
	return datetime.datetime(int(segs[5]), _MONS.index(segs[1]), int(segs[2]), int(ts[0]), int(ts[1]), int(ts[2]))

def normalizedir(mblog):
	nick = mblog['user']['screen_name']
	nick = re.sub('^[·_-]+', '', nick)
	nick = re.sub('[·_-]+$', '', nick)
	return '{}#{}'.format(nick, mblog['user']['id'])

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

def parseuids():
	idsarg = sys.argv[2:]
	if len(idsarg) > 0:
		return [eval(i) for i in idsarg]
	else:
		with open(WBPIC_DIR + os.sep + 'wbpic-uids.json') as f:
			return pyjson5.load(f)

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
		with  session.get(self.url, stream=True) as r:
			size_expected = int(r.headers['Content-Length'])
		if r.status_code < 200 or r.status_code > 299:
			log('ERROR', '{} invalid {}, failed {}', self.file_path, r, self.url)
			return
		if ignoring and ignoring(size_expected):
			log('WARN', '{} too small [{}], ignored {}', self.file_path, size(size_expected), self.url)
			return
		size_curr = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
		if size_curr > size_expected:
			log('WARN', '{} current size {} exceed expected {}, ignored {}', self.file_path, size(size_curr), size(size_expected), self.url)
			return	
		if size_curr == size_expected:
			log('TRACE', '{} existed and size {} match, ignore {}', self.file_path, size(size_curr), self.url)
			return
		size_needs = size_expected - size_curr
		try:
			while size_curr < size_expected:
				if size_curr == 0:
					msg = "%s total %s fetching..." % (self.file_path, size(size_expected))
				else:
					msg = "%s total %d and existed %d, %2.2f%% progressing..." % (self.file_path, size(size_expected), size(size_curr), 100 * size_curr / size_expected)
				log('DEBUG', msg)

				if (size_curr > 0): self.headers['Range'] = 'bytes=%d-' % size_curr
				try:
					with session.get(self.url, stream=True, headers=self.headers) as r, open(self.file_path, "ab") as f:
						shutil.copyfileobj(r.raw, f)
				except Exception as e:
					log('ERROR', '{} fetching failed to {} for erro {}, \n\ttotal {} bytes and {} bytes fetched.', self.url, self.file_path, e, size_expected, size_curr)
				finally:
					size_curr = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
		finally:
			os.utime(self.file_path, (int(self.created.timestamp()), int(self.created.timestamp())))
			log('DEBUG', '{} fetched finished, {} bytes this time and {} bytes total from {}', self.file_path, size(size_needs), size(size_curr), self.url)
