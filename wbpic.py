import sys, json
from wb.context import opts, finalize
from wb.parser import list, list1, follows
from wb.utils import log, parsesince, parseuids

def followings():
	print(json.dumps(follows(), indent=2, ensure_ascii=False))

sum = 0
try:
	if len(sys.argv) == 2 and sys.argv[1].startswith('#'): sum = list1(sys.argv[1][1:])
	else:
		since = parsesince()
		uids = parseuids(sys.argv[2:], lambda n: n.startswith('['))
		total = len(uids)
		c = 0
		if isinstance(uids, dict):
			for uid, dir in uids.items():
				c += 1
				if ('skip' in opts and c <= opts['skip']): continue
				sum += list(uid, since, '[{}/{}]'.format(c, total), dir=dir)
		else:
			for uid in uids:
				c += 1
				if ('skip' in opts and c <= opts['skip']): continue
				sum += list(uid, since, '[{}/{}]'.format(c, total))
finally:
	log('INFO', 'Whole parsing finished, {} pictures found.', sum)
	finalize()
