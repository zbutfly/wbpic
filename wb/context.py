import os
import multiprocessing.dummy as mproc
import pyjson5
from wb.utils import log, WBPIC_DIR, loglevel
from wb.fetcher import session

opts = {}
with open(WBPIC_DIR + os.sep + 'conf' + os.sep + 'wbpic-opts.json') as f:
	opts = pyjson5.load(f)
if 'log_level' in opts:
	loglevel(opts['log_level'])
headers_pics_curl = ' -x ' + opts['proxy'] if 'proxy' in opts else ''
for n in opts['headers_pics']:
	headers_pics_curl = headers_pics_curl + \
         ' -H "{}: {}"'.format(n, opts['headers_pics'][n])
log('DEBUG', 'CURL_OPTS={}', headers_pics_curl)
CURL_CMD = 'curl "{}" -o "{}" --fail -k -s -R --show-error --retry 999 --retry-max-time 0 -C -' + headers_pics_curl

session.trust_env = not 'proxy' in opts or opts['proxy'].lower() == 'sys'
if not session.trust_env and opts.get('proxy') != '':
	session.proxies.update({"https": opts.get('proxy'), "http": opts.get('proxy')})

# def opencheck():
# 	ids = None
# 	if not bool(opts.get('checking', False)): return
# 	flogname = basedir + os.sep + 'checked.log'
# 	if os.path.exists(flogname):
# 		with open(flogname) as f:
# 			ids = [line.rstrip() for line in f]
# 	return ids, open(flogname, 'a')
# checkpids, checklogf = opencheck()

sum_bytes = 0
sum_pics = 0
