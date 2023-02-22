import sys, os, time, calendar, datetime, random, re, json, pyjson5, requests
from colorama import Fore as fcolor

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
	levcolor = _LEVEL_COLORS.get(level.upper)
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
