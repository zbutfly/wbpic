from wb.context import opts, finalize
from wb.parser import listall, follows
from wb.utils import log

## TODO
# 1. VIP图片分析
# 2. VIP首图403问题
# 3. Live Video换成图片
# 4. HTTP 418 反爬虫等待重试

try:
	# if len(sys.argv) == 2 and
	listall()
	# print(json.dumps(follows(), indent=2, ensure_ascii=False))
finally:
	finalize()
