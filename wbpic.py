import requests, sys, platform, time, os, json, re, calendar, datetime, math, operator, random


## entry url
# 微博列表 https://m.weibo.cn/api/container/getIndex?containerid=230413{}_-_WEIBO_SECOND_PROFILE_WEIBO&page={}
URL_WB_LIST = 'https://m.weibo.cn/api/container/getIndex?containerid=230413{}_-_WEIBO_SECOND_PROFILE_WEIBO_ORI&since_id={}'
URL_WB_ITEM = 'https://m.weibo.cn/detail/{}'
CURL_CMD = 'curl "{}" -o "{}" --fail -s -R --show-error --retry 999 --retry-max-time 0 -C -'


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
	opts = json.load(f, )
with open(WBPIC_DIR + os.sep + 'wbpic-uids.json') as f:
	uids = json.load(f)

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
				print('REM #ERROR: ', dirname, '{}[{}]'.format(bid, pi), created, file=sys.stderr)
				continue
		fext = os.path.splitext(pic['large']['url'])[1].split('?')[0]
		fname = created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(bid, pi + 1, pic['pid'], fext)
		img = {
			'id': pic['pid'],
			'url': pic['large']['url'],
			'width': pic['large']['geo']['width'],
			'height': pic['large']['geo']['height'],
			'dirname': dirname,
			'filename': 
		}
		if (pic['large']['geo']['width'] > 480 and pic['large']['geo']['height'] > 480):
			print(CURL_CMD.format(img['url'], img['dirname'] + os.sep + img['filename']))

def normalizedir(mblog):
	nickname = re.sub('^[·_-]+', '', mblog['user']['screen_name'])
	nickname = re.sub('[·_-]+$', '', mblog['user']['screen_name'])
	return '{}-{}'.format(nickname, mblog['user']['id'])

def list(userid, after=datetime.datetime.today().date() - datetime.timedelta(1)): # defalt yesterday to now
	dir_made = False
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

# before = datetime.datetime.strptime(sys.argv[1], '%Y%m%d').date()
# for uid in uids:
# 	list(uid, before)
		
sample = list(sys.argv[1], datetime.datetime.strptime('20230201', '%Y%m%d').date())
# print(json.dumps(sample, indent=2, default=str))