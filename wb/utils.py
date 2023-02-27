import sys, signal, os, calendar, datetime, re, pyjson5
from timeit import default_timer as timer
from colorama import Fore as fcolor
import wb.statistics as statistics


def sigign():
	signal.signal(signal.SIGINT, signal.SIG_IGN)


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

_LEVEL_GRADE = {'TODO': 99, 'TRACE': -2, 'DEBUG': -1, 'INFO': 0, 'WARN': 1, 'ERROR': 2}

_LOG_LEVEL = None


def loglevel(level):
	global _LOG_LEVEL
	_LOG_LEVEL = level.upper()


def log(level, format, *vars):
	if _LOG_LEVEL and _LEVEL_GRADE[level.upper()] < _LEVEL_GRADE[_LOG_LEVEL.upper()]:
		return
	level = level if level else 'INFO'
	levcolor = _LEVEL_COLORS[level.upper()]
	# if tpool:
	# msg = '{} {} [{}] '.format(_c(fcolor.BLUE, 'REM'), threading.current_thread(), _c(levcolor, level)) + _c(levcolor, format)
	# else:
	msg = '{} [{}] '.format(_c(fcolor.BLUE, 'REM'), _c(levcolor, level)) + _c(levcolor, format)
	print(msg.format(*vars), file=sys.stderr)


def parsesince() -> datetime.date:
	if len(sys.argv) <= 1:
		since = '1'  # default yesterday
	elif sys.argv[1] != '':
		since = sys.argv[1]
	else:
		since = '20090801'  # weibo init on 20090814
	if eval(since) < 9999:  # days
		since = datetime.datetime.today().date() - datetime.timedelta(eval(since))
	else:
		since = datetime.datetime.strptime(since, '%Y%m%d').date()
	log('INFO', 'since {}, start at {}', since, datetime.datetime.now())
	return since


def parsedirs(basedir, accepting=None) -> dict:
	uids = {}
	for cats in [f.path for f in os.scandir(basedir) if f.is_dir() and (not accepting or accepting(f.name))]:
		for entry in [ff for ff in os.scandir(cats) if ff.is_dir()]:
			m = re.findall(r'#(\d{10})', entry.name)  #, flags=re.DOTALL
			if m:
				for uid in m:
					p = entry.path.replace(basedir, '', 1) if entry.path.startswith(basedir) else entry.path
					if uid in uids:
						log('ERROR', 'duplicated userid {} tag in {} (use this) and {}', uid, uids[uid], p)
					else:
						uids[uid] = p
	return uids


def parseuids(idsarg, accepting=None):  # -> list or dict, item: int ot str
	if len(idsarg) > 0:
		if len(idsarg) == 1 and idsarg[0].startswith('@'):
			if not idsarg[0].endswith(os.sep):
				with open(idsarg[0][1:]) as f:
					return pyjson5.load(f)
			else:
				return parsedirs(idsarg[0][1:], accepting)
		else:
			return [eval(i) for i in idsarg]
	else:
		with open(WBPIC_DIR + os.sep + os.sep + 'wbpic-uids.json', encoding='UTF-8') as f:
			return pyjson5.load(f)
