import requests, sys, platform, time, os, json, re, calendar, datetime, math, operator, random


## entry url
# 微博列表 https://m.weibo.cn/api/container/getIndex?containerid=230413{}_-_WEIBO_SECOND_PROFILE_WEIBO&page={}
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
if ('proxy' in opts):
	headers_pics_curl = ' -x ' + opts['proxy']
else:
	headers_pics_curl = ''
for n in opts['headers_pics']:
	headers_pics_curl = headers_pics_curl + ' -H "{}: {}"'.format(n, opts['headers_pics'][n])
print('REM #DEBUG: CURL_OPTS=', headers_pics_curl, file=sys.stderr)
CURL_CMD = 'curl "{}" -o "{}" --fail -s -R --show-error --retry 999 --retry-max-time 0 -C -' + headers_pics_curl

session = requests.Session()
session.trust_env = not 'proxy' in opts or opts['proxy'].lower() == 'sys'
if (not session.trust_env and opts.get('proxy') != ''):
	session.proxies.update({"https": opts.get('proxy'), "http": opts.get('proxy')})

# created_at: "Sun Dec 25 00:54:56 +0800 2022"
MONS = list(calendar.month_abbr)
def parseTime(createdStr):
	# datetime.strptime(createdStr, '%a %b %d %H:%M:%s %z %Y')
	segs = createdStr.split(' ')
	ts = segs[3].split(':')
	return datetime.datetime(int(segs[5]), MONS.index(segs[1]), int(segs[2]), int(ts[0]), int(ts[1]), int(ts[2]))

def pic(pics, dirname, created, bid, pindex):
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
		if (ext.lower() == '.gif'):
			print('REM #WARN: ', dirname, '{}[{}]'.format(bid, pi), created, ' gif ignored.', file=sys.stderr)
			continue
		filename = created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(bid, pi + 1, pic['pid'], ext)
		img = {
			'id': pic['pid'],
			'url': pic['large']['url'],
			'width': int(pic['large']['geo']['width']),
			'height': int(pic['large']['geo']['height']),
			'dirname': dirname,
			'filename': filename
		}
		if (img['width'] > 480 and img['height'] > 480):
			imgpath = img['dirname']
			if ('basedir' in opts):
				imgpath = opts['basedir'] + os.sep + imgpath
			if (not os.path.isdir(imgpath)):
				os.makedirs(imgpath, exist_ok=True)
			imgpath = imgpath + os.sep + img['filename']
			print(CURL_CMD.format(img['url'], imgpath))
		else:
			print('REM #WARN: ', dirname, '{}[{}]'.format(bid, pi), created, ' small ignored.', file=sys.stderr)

def normalizedir(mblog):
	nickname = mblog['user']['screen_name']
	nickname = re.sub('^[·_-]+', '', nickname)
	nickname = re.sub('[·_-]+$', '', nickname)
	return '{}-{}'.format(nickname, mblog['user']['id'])

def list(userid, after): # defalt yesterday to now
	since_id = ''
	while (True):
		target = URL_WB_LIST.format(userid, since_id)
		print('REM #DEBUG: ', target, 'is parsing', file=sys.stderr)
		response = session.get(target, headers = None, stream = False, verify = False)
		if (response.status_code < 200 or response.status_code > 299):
			return
		try:
			jsonresp = json.loads(response.text)
		except json.decoder.JSONDecodeError:
			print('#ERROR: ', response.text, file=sys.stderr)
			
		if (1 != jsonresp['ok']):
			return
		dirname = ''
		for card in jsonresp['data']['cards']:
			if (not 'mblog' in card):
				continue
			mblog = card['mblog']
			if (not 'pics' in mblog):
				continue
			newdir = normalizedir(mblog)
			if (dirname == ''):
				dirname = newdir
			elif (dirname != newdir):
				print('REM #WARN: diff user: ', dirname, newdir, file=sys.stderr)
			created = parseTime(mblog['created_at'])
			if (created.date() < after):
				print('REM #DEBUG: ', dirname, 'exceed: ', created.date(), file=sys.stderr)
				return

			pic(mblog['pics'], dirname, created, mblog['bid'], 0)
			if (mblog['pic_num'] > 9):
				# https://m.weibo.cn/status/{}
				wburl =  card['scheme'] # https://m.weibo.cn/detail/4850366267002849
				# print('REM #TODO: checking {} for {} pics'.format(wburl, mblog['pic_num']))
				with session.get(wburl) as r:
					m = re.search(r'var \$render_data = \[(.+)\]\[0\] \|\| {};', r.text, flags=re.DOTALL)
					if not m:
						print('REM #ERROR Cannot parse post. Try to set cookie.', wburl, r, '\n\t', r.text, file=sys.stderr)
					else:
						pic(json.loads(m[1])['status']['pics'][9:], dirname, created, mblog['bid'], 8)
		if (not 'since_id' in jsonresp['data']['cardlistInfo']):
			print('REM #DEBUG: ', dirname, 'finished whole weibo history.', file=sys.stderr)
			return
		since_id = jsonresp['data']['cardlistInfo']['since_id']
		time.sleep(abs(random.gauss(0.5, 0.3)))
	time.sleep(random.gauss(0.6, 1))

## 孔雀死孔雀:	2971240104
## 三無人型：	5270294200
## 轩萧学姐:	5604678555

def __main__():
	if (len(sys.argv) <= 1):
		after = '1' # default yesterday
	elif (sys.argv[1] != ''):
		after = sys.argv[1]
	else:
		after = '20090801' # weibo init on 20090814
	if (eval(after) < 9999): # days
		after = datetime.datetime.today().date() - datetime.timedelta(eval(after))
	else:
		after = datetime.datetime.strptime(after, '%Y%m%d').date()

	idsarg = sys.argv[2:]
	if (len(idsarg) > 0):
		uids = [eval(i) for i in idsarg]
	else:
		with open(WBPIC_DIR + os.sep + 'wbpic-uids.json') as f:
			uids = json.load(f)

	for uid in uids:
		list(uid, after)

# list(7575160994, datetime.datetime.strptime('20000101', '%Y%m%d').date())
# print(json.dumps(sample, indent=2, default=str))

__main__()

print('REM #INFO Whole parsing finished, run the curl script to download.', file=sys.stderr)

