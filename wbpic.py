import sys, json
from wb.context import opts, finalize
from wb.parser import list, list1, follows
from wb.utils import log, parsesince, parseuids

def followings():
	print(json.dumps(follows(), indent=2, ensure_ascii=False))

try:
	sum = 0
	if len(sys.argv) == 2 and sys.argv[1].startswith('#'): sum = list1(sys.argv[1][1:])
	else:
		since = parsesince()
		uids = parseuids(sys.argv[2:], lambda n: n.startswith('['))
		# print(json.dumps(uids, indent=2, ensure_ascii=False))
		# exit()
		total = len(uids)
		for uid in uids:
			sum += list(uid, since, total)
	log('INFO', 'Whole parsing finished, {} pictures found.', sum)
finally:
	finalize()
