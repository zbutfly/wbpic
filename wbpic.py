from wb.context import opts, finalize
from wb.parser import listall, follows
from wb.utils import log

try:
	# if len(sys.argv) == 2 and
	listall()
	# print(json.dumps(follows(), indent=2, ensure_ascii=False))
finally:
	finalize()
