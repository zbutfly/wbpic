import os, pyjson5
from wb.utils import log, httpget, session, WBPIC_DIR, loglevel

URL_WB_LIST = 'https://m.weibo.cn/api/container/getIndex?containerid=230413{}_-_WEIBO_SECOND_PROFILE_WEIBO_ORI&since_id={}'
# https://m.weibo.cn/detail/4850366267002849 or https://m.weibo.cn/status/{}
# https://m.weibo.cn/statuses/show?id={mblog[bid]}	MtjjJhg2n JSON
URL_WB_ITEM = 'https://m.weibo.cn/statuses/show?id={}'
URL_WB_ITEM_HIS = 'https://m.weibo.cn/api/container/getIndex?containerid=231440_-_{}'
URL_FOLLOWERS = 'https://m.weibo.cn/api/container/getIndex?containerid=231093_-_selffollowed&page={}'

opts = {}
with open(WBPIC_DIR + os.sep + 'conf' + os.sep + 'wbpic-opts.json') as f:
	opts = pyjson5.load(f)
if 'log_level' in opts: loglevel(opts['log_level'])
headers_pics_curl = ' -x ' + opts['proxy'] if 'proxy' in opts else ''
for n in opts['headers_pics']:
	headers_pics_curl = headers_pics_curl + ' -H "{}: {}"'.format(n, opts['headers_pics'][n])
log('DEBUG', 'CURL_OPTS={}', headers_pics_curl)
CURL_CMD = 'curl "{}" -o "{}" --fail -k -s -R --show-error --retry 999 --retry-max-time 0 -C -' + headers_pics_curl

session.trust_env = not 'proxy' in opts or opts['proxy'].lower() == 'sys'
if not session.trust_env and opts.get('proxy') != '':
	session.proxies.update({"https": opts.get('proxy'), "http": opts.get('proxy')})

checkpids = []
checklogf = None
basedir = WBPIC_DIR + os.sep + (opts['basedir'] if 'basedir' in opts else "wbpics")
if bool(opts.get('checking', False)):
	flogname = basedir + os.sep + 'checked.log'
	if os.path.exists(flogname):
		with open(flogname) as checklogf:
			checkpids = [line.rstrip() for line in checklogf]
	checklogf = open(flogname, 'a')

def finalize():
	if checklogf: checklogf.close()

_HTTP_SLEEP_SECS = opts.get('interval', 0.4)
_RETRY_MAX = opts.get('retry', 3)
_HTTP_HEADERS_AUTH = opts.get('headers_auth')

def getjson(url):
	response = httpget(url, _HTTP_HEADERS_AUTH, _HTTP_SLEEP_SECS, _RETRY_MAX)
	try:
		result = pyjson5.loads(response)
		if result: return result
		log('ERROR', 'json invalid: {}\n{}', url, response)
	except Exception as e:
		log('ERROR', '{} json parse failed:\n{}', url, response)