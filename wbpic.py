import requests, sys, platform, time, os, json, re, calendar, datetime, math, operator


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


with open('wbpic-opts.json') as f:
	opts = json.load(f, )
with open('wbpic-uids.json') as f:
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

def list(userid, after=datetime.datetime.today().date() - datetime.timedelta(1)): # defalt yesterday to now
	dir_made = False
	wbs = []
	since_id = ''
	while (True):
		target = URL_WB_LIST.format(userid, since_id)
		response = session.get(target, headers = None, stream = False, verify = False)
		if (response.status_code < 200 or response.status_code > 299):
			return wbs
		jsonresp = json.loads(response.text)
		if (1 != jsonresp['ok']):
			return wbs
		since_id = jsonresp['data']['cardlistInfo']['since_id']
		dirname = ''
		##### print(json.dumps(jsonresp, indent=2))
		for card in jsonresp['data']['cards']:
			mblog = card['mblog']
			if (not 'pics' in mblog):
				continue
			if (dirname == ''):
				dirname = '{}-{}'.format(mblog['user']['screen_name'], mblog['user']['id'])
			elif (dirname != '{}-{}'.format(mblog['user']['screen_name'], mblog['user']['id'])):
				print('#WARN: diff user: ', dirname, '{}-{}'.format(mblog['user']['screen_name'], mblog['user']['id']))
			if (not dir_made and not os.path.isdir(dirname)):
				os.makedirs(dirname, exist_ok=True)
				dir_made = True
			created = parseTime(mblog['created_at'])
			if (created.date() < after):
				print('#DEBUG: ', 'exceed: ', created.date())
				return wbs

			wb = {
				'created_at': created,
				'bid': mblog['bid'],
				'mid': mblog['mid'],
				'pics': []
			}
			pindex = 0
			for pic in mblog['pics']:
				pindex = pindex + 1
				img = {
					'id': pic['pid'],
					'index': pindex, 
					'url': pic['large']['url'],
					'width': pic['large']['geo']['width'],
					'height': pic['large']['geo']['height'],
					'dirname': dirname,
					'filename': created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(wb['bid'], pindex, pic['pid'], os.path.splitext(pic['large']['url'])[1])
				}
				wb['pics'].append(img)
			if (mblog['pic_num'] > 9):
				# https://m.weibo.cn/status/{}
				wburl =  card['scheme'] # https://m.weibo.cn/detail/4850366267002849
				# print('#TODO: checking {} for {} pics'.format(wburl, mblog['pic_num']))
				with session.get(wburl) as r:
					m = re.search(r'var \$render_data = \[(.+)\]\[0\] \|\| {};', r.text, flags=re.DOTALL)
					if not m:
						print('#ERROR Cannot parse post. Try to set cookie.')
					else:
						for pic in json.loads(m[1])['status']['pics'][9:]:
							pindex = pindex + 1
							img = {
								'id': pic['pid'],
								'index': pindex,
								'url': pic['large']['url'],
								'width': pic['large']['geo']['width'],
								'height': pic['large']['geo']['height'],
								'dirname': dirname,
								'filename': created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(wb['bid'], pindex, pic['pid'], os.path.splitext(pic['large']['url'])[1])
							}
							wb['pics'].append(img)
			wbs.append(wb)
	return wbs

## 孔雀死孔雀:	2971240104
## 三無人型：	5270294200
## 轩萧学姐:	5604678555

# -x http://pc-hz20099585:8899
def all():
	for uid in uids:
		for wb in list(5270294200, datetime.datetime.strptime(sys.argv[1], '%Y%m%d').date()):
			for pic in wb['pics']:
				try:
					response = session.get(pic['url'], headers = opts['headers_pics'], stream = False, verify = False)
					assert response.status_code != 418
					result = json.loads(response.text)
				except AssertionError:
					print('#WARN: punished by anti-scraping mechanism (#{})'.format(pic))
				except Exception:
					pass
				else:
					print(CURL_CMD.format(pic.url, pic['dirname'] + os.sep + pic['filename']))
				# finally:
				# 	time.sleep(1);

# all()
		
sample = list(5270294200, datetime.datetime.strptime(sys.argv[1], '%Y%m%d').date())
# print(json.dumps(sample, indent=2, default=str))