import requests, sys, platform, time, os, json, re, calendar, datetime, math, operator, random

## TODO
# 1. VIP图片分析
# 2. VIP首图403问题
# 3. Live Video换成图片
# 4. HTTP 418 反爬虫等待重试

## entry url
# 全部微博		https://m.weibo.cn/p/230413{}_-_WEIBO_SECOND_PROFILE_WEIBO&page={}
# 原创微博		https://m.weibo.cn/p/230413{}_-_WEIBO_SECOND_PROFILE_WEIBO_ORI&since_id={}
# 全部微博JSON	https://m.weibo.cn/api/container/getIndex?containerid=230413{}_-_WEIBO_SECOND_PROFILE_WEIBO&page={}
URL_WB_LIST = 'https://m.weibo.cn/api/container/getIndex?containerid=230413{}_-_WEIBO_SECOND_PROFILE_WEIBO_ORI&since_id={}'
URL_WB_ITEM = 'https://m.weibo.cn/detail/{}'


if platform.system() == 'Windows':
	if operator.ge(*map(lambda version: list(map(int, version.split('.'))), [platform.version(), '10.0.14393'])):
		os.system('')
	else:
		import colorama
		colorama.init()
try:
	requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
except:
	pass

WBPIC_DIR = os.path.dirname(os.path.realpath(__file__))
with open(WBPIC_DIR + os.sep + 'wbpic-opts.json') as f:
	opts = json.load(f)
if 'proxy' in opts:
	headers_pics_curl = ' -x ' + opts['proxy']
else:
	headers_pics_curl = ''
for n in opts['headers_pics']:
	headers_pics_curl = headers_pics_curl + ' -H "{}: {}"'.format(n, opts['headers_pics'][n])
print('REM #DEBUG: CURL_OPTS=', headers_pics_curl, file=sys.stderr)
CURL_CMD = 'curl "{}" -o "{}" --fail -k -s -R --show-error --retry 999 --retry-max-time 0 -C -' + headers_pics_curl

session = requests.Session()
session.trust_env = not 'proxy' in opts or opts['proxy'].lower() == 'sys'
if not session.trust_env and opts.get('proxy') != '':
	session.proxies.update({"https": opts.get('proxy'), "http": opts.get('proxy')})

# created_at: "Sun Dec 25 00:54:56 +0800 2022"
MONS = list(calendar.month_abbr)
def parseTime(createdStr):
	# datetime.strptime(createdStr, '%a %b %d %H:%M:%s %z %Y')
	segs = createdStr.split(' ')
	ts = segs[3].split(':')
	return datetime.datetime(int(segs[5]), MONS.index(segs[1]), int(segs[2]), int(ts[0]), int(ts[1]), int(ts[2]))

CURL_PRINT_COUNT=0
def pic(pics, dirname, created, bid, pindex):
	global CURL_PRINT_COUNT
	for pi in range(pindex, len(pics)):
		try:
			pic = pics[pi]
		except:
			try:
				pic = pics[str(pi)]
			except:
				print('REM #WARN: ', dirname, '{}[{}]'.format(bid, pi), created, ' live video ignored: ', pic['large']['url'], file=sys.stderr)
				continue
		ext = os.path.splitext(pic['large']['url'])[1].split('?')[0]
		if ext.lower() == '.gif':
			print('REM #WARN: ', dirname, '{}[{}]'.format(bid, pi), created, ' gif ignored.', file=sys.stderr)
			continue
		if (pic['large']['url'].startswith('https://zzx.')):
			ext = '[zzx]' + ext
		filename = created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(bid, pi + 1, pic['pid'], ext)
		img = {
			'id': pic['pid'],
			'url': pic['large']['url'],
			'width': int(pic['large']['geo']['width']),
			'height': int(pic['large']['geo']['height']),
			'dirname': dirname,
			'filename': filename
		}
		
		if img['width'] > opts.get('min_dimension', 360) and img['height'] > opts.get('min_dimension', 360):
			imgpath = img['dirname']
			if 'basedir' in opts:
				imgpath = opts['basedir'] + os.sep + imgpath
			if not os.path.isdir(imgpath):
				os.makedirs(imgpath, exist_ok=True)
			imgpath = imgpath + os.sep + img['filename']
			print(CURL_CMD.format(img['url'], imgpath))
			CURL_PRINT_COUNT = CURL_PRINT_COUNT + 1
		else:
			print('REM #WARN: ', dirname, '{}[{}]'.format(bid, pi), created, ' small ignored.', file=sys.stderr)

def normalizedir(mblog):
	nickname = mblog['user']['screen_name']
	nickname = re.sub('^[·_-]+', '', nickname)
	nickname = re.sub('[·_-]+$', '', nickname)
	return '{}-{}'.format(nickname, mblog['user']['id'])

HTTP_SLEEP_SECS = 0.4
RETRY_MAX = 5
def httpget(target):
	retry = 0
	while retry < RETRY_MAX:
		try:
			with session.get(target, headers = opts.get('headers_auth'), stream = False, verify = False) as r:
				if r.status_code != 418:
					retry = RETRY_MAX
					if r.status_code < 200 or r.status_code > 299:
						print('REM #ERROR: ', target, 'fetch incorrectly', r, r.text, file=sys.stderr)
						return
					return r.text
				else:
					retry = retry + 1
					print('REM #ERROR: ', target, r, ' retry #', retry, file=sys.stderr)
		except Exception as e:
			print('REM #ERROR: ', target, r, r.text, '\n\t', e, file=sys.stderr)
			return
		finally:
			time.sleep(abs(random.gauss(HTTP_SLEEP_SECS, HTTP_SLEEP_SECS/2.5)))


def list(userid, after): # defalt yesterday to now
	since_id = ''
	while (True):
		target = URL_WB_LIST.format(userid, since_id)
		print('REM #DEBUG: ', target, 'is parsing', file=sys.stderr)
		jsonstr = httpget(target)
		jsonobj = json.loads(jsonstr)
		if not jsonobj:
			print('REM #ERROR: ', target, 'json invalid', '\n', jsonstr, file=sys.stderr)
			return
			
		if 1 != jsonobj['ok']:
			return
		dirname = ''
		for card in jsonobj['data']['cards']:
			if not 'mblog' in card:
				continue
			mblog = card['mblog']
			if not 'pics' in mblog:
				continue
			newdir = normalizedir(mblog)
			if dirname == '':
				dirname = newdir
			elif dirname != newdir:
				print('REM #WARN: diff user: ', dirname, newdir, file=sys.stderr)
			created = parseTime(mblog['created_at'])
			if created.date() < after:
				print('REM #DEBUG: ', dirname, 'exceed: ', created.date(), file=sys.stderr)
				return

			pic(mblog['pics'], dirname, created, mblog['bid'], 0)
			if mblog['pic_num'] > 9:
				# https://m.weibo.cn/status/{}
				wburl = card['scheme'] # https://m.weibo.cn/detail/4850366267002849
				# print('REM #TODO: checking {} for {} pics'.format(wburl, mblog['pic_num']))
				html = httpget(wburl)
				m = re.search(r'var \$render_data = \[(.+)\]\[0\] \|\| {};', html, flags=re.DOTALL)
				if not m:
					print('REM #ERROR Cannot parse post. Try to set cookie.', wburl, '\n', html, file=sys.stderr)
				else:
					pic(json.loads(m[1])['status']['pics'], dirname, created, mblog['bid'], 9)
		if not 'since_id' in jsonobj['data']['cardlistInfo']:
			print('REM #DEBUG: ', dirname, 'finished whole weibo history.', file=sys.stderr)
			return
		since_id = jsonobj['data']['cardlistInfo']['since_id']

def __main__():
	if len(sys.argv) <= 1:
		after = '1' # default yesterday
	elif sys.argv[1] != '':
		after = sys.argv[1]
	else:
		after = '20090801' # weibo init on 20090814
	if eval(after) < 9999: # days
		after = datetime.datetime.today().date() - datetime.timedelta(eval(after))
	else:
		after = datetime.datetime.strptime(after, '%Y%m%d').date()
	print('REM #INFO: after', after, file=sys.stderr)
	idsarg = sys.argv[2:]
	if len(idsarg) > 0:
		uids = [eval(i) for i in idsarg]
	else:
		with open(WBPIC_DIR + os.sep + 'wbpic-uids.json') as f:
			uids = json.load(f)

	for uid in uids:
		list(uid, after)

# list(7575160994, datetime.datetime.strptime('20000101', '%Y%m%d').date())
# print(json.dumps(sample, indent=2, default=str))

__main__()

print('REM #INFO Whole parsing finished, run the curl script to download, {} pictures.'.format(CURL_PRINT_COUNT), file=sys.stderr)

