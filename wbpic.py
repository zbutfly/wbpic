import requests, sys, platform, time, os, json, re, calendar, datetime, math, operator

## containerId
# 100505 个人主页信息
# 107603 首页微博列表（无isTop标识）
# 230283
# 230413 微博列表
# 231522

## entry url
# 微博列表 https://m.weibo.cn/api/container/getIndex?containerid=230413{}_-_WEIBO_SECOND_PROFILE_WEIBO&page={}
URL_WB_LIST = 'https://m.weibo.cn/api/container/getIndex?containerid=230413{}&page={}'

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


with open('wbpic-opts.json') as f:
	opts = json.load(f)
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
	page = 1
	while (True):
		target = URL_WB_LIST.format(userid, page)
		page = page + 1
		response = session.get(target, headers = None, stream = False, verify = False)
		if (response.status_code < 200 or response.status_code > 299):
			return wbs
		jsonresp = json.loads(response.text)
		if (1 != jsonresp['ok']):
			return wbs
		dirname = ''
		##### print(json.dumps(jsonresp, indent=2))
		for card in jsonresp['data']['cards']:
			if (card['card_type'] != 9):
				continue
			mblog = card['mblog']
			if (dirname == ''):
				dirname = '{}-{}'.format(mblog['user']['screen_name'], mblog['user']['id'])
			else:
				print("#WARN: diff user: ", dirname, '{}-{}'.format(mblog['user']['screen_name'], mblog['user']['id']))
			if (not dir_made and os.path.isdir('new_folder')):
				os.makedirs(dirname, exist_ok=True)
				dir_made = True
			##### print('\n\n=> ', mblog)
			# if ('isTop' in mblog and mblog['isTop'] == 1):
			# 	continue
			# card_type = 9
			# isTop != 1
			# exclude: mblog.retweeted_status
			# exclude: mblog.action_info
			if ('retweeted_status' in mblog or 'action_info' in mblog or not 'pics' in mblog):
				continue
			created = parseTime(mblog['created_at'])
			if (created.date() < after):
				if ('isTop' in mblog and mblog['isTop'] == 1):
					continue
				else:
					print('====> ', 'exceed: ', created.date())
					return wbs
			# return: mblog.created_at/bid/mid, mblog.pic_num(18?), mblog.pics[].large.url, mblog.pics[].large.geo.width/height
			wb = {
				'created_at': created,
				'bid': mblog['bid'],
				'mid': mblog['mid'],
				'pics': []
			}
			pindex = 0
			for pic in mblog['pics']:
				pindex = pindex + 1
				wb['pics'].append({
					'id': pic['pid'],
					'url': pic['large']['url'],
					'width': pic['large']['geo']['width'],
					'height': pic['large']['geo']['height'],
					'dirname': dirname,
					'filename': created.strftime('%Y%m%d_%H%M%S-{}-{}-{}{}').format(wb['bid'], pindex, pic['pid'], os.path.splitext(pic['large']['url'])[1])
				})
			if (mblog['pic_num'] > 9):
				wburl = 'https://m.weibo.cn/detail/{}'.format(wb.mid) # https://m.weibo.cn/detail/4850366267002849
				print('#TODO: checking {} for more than 9 pics'.format(wburl))
				# retun: egrep --color=NONE -o "url\": \"https://.*/large/[^\"]*" "4850366267002849.html"
			wbs.append(wb)
	return wbs

## 孔雀死孔雀:	2971240104
## 三無人型：	5270294200
## 轩萧学姐:	5604678555
sample = list(5270294200, datetime.datetime.strptime(sys.argv[1], '%Y%m%d').date())
# print(json.dumps(sample, indent=2, default=str))
