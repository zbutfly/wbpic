import os, random, time, dateutil, requests, shutil, copy
from timeit import default_timer as timer
import wb.statistics as statistics
from wb.utils import log

session = requests.Session()

class Fetcher(object):
	@classmethod
	def gethttp(target, headers, retry, interval):
		retried = 0
		now = timer()
		while retried < retry:
			try:
				with session.get(target, headers = headers, stream = False, verify = False) as r:
					spent = timer() - now
					if r.status_code == 418 or r.status_code > 500: # retry only for spam or server-side error
						retried = retried + 1
						log('WARN', '{} retry #{}, result {}', target, retried, r)
						time.sleep(abs(random.gauss(interval*10, interval*4)))
						continue
					if r.status_code < 200 and r.status_code >= 300:
						log('ERROR', '{} fetch incorrectly spent {} secs return {}, {}', target, statistics.ftimedelta(spent), r, r.text)
						return
					if (spent > 0.5): log('INFO' if spent < 1 else 'WARN', 'fetch slow spent {} secs return {}: {}', statistics.ftimedelta(spent), r, target)
					return r.text
			except Exception as e:
				log('ERROR', '{} spent {} secs and failed {}', target, statistics.ftimedelta(timer() - now), e)
				return
			finally:
				time.sleep(abs(random.gauss(interval, interval/2.5)))
		log('ERROR', '{} failed after retries {} and spent {} secs.', target, retried, statistics.ftimedelta(timer() - now))

	def __init__(self, url, file_path, created, headers, forcing, ignoring=None):
		self.url = url
		self.file_path = file_path
		self.headers = copy.deepcopy(headers)
		self.created = created
		self.forcing = forcing
		# self.auth_headers = auth_headers

		self.size_begin = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
		self.size_expected = -1 if self.forcing else self.sizeremote()
		self.size_needs = self.sizecheck(ignoring)

	def remotetime(self, r):
		last_modified = r.headers.get('Last-Modified')
		return dateutil.parser.parse(last_modified) if last_modified else None

	def sizeremote(self): # return size_expected
		try:
			with session.head(self.url, stream=True, headers=self.headers) as r:
				r.raise_for_status()
				return int(r.headers['Content-Length']) if 'Content-Length' in r.headers else -1
		except Exception as e:
			log('ERROR', '{} HEAD fetching failed {} for error {}.', self.file_path, self.url, e)
			return -1

	def sizecheck(self, ignoring): # return size_needs
		if self.size_expected < 0: return -1
		if ignoring and ignoring(self.size_expected):
			log('DEBUG', '{} HEAD too small [{}], ignored {}', self.file_path, statistics.fbytes(self.size_expected), self.url)
			return 0
		if self.size_begin > self.size_expected:
			log('DEBUG', '{} HEAD current size {} exceed expected {}, ignored {}', self.file_path, statistics.fbytes(self.size_begin), statistics.fbytes(self.size_expected), self.url)
			return 0
		if self.size_begin == self.size_expected:
			log('TRACE', '{} HEAD existed and size {} match, ignore {}', self.file_path, statistics.fbytes(self.size_begin), self.url)
			return 0
		return self.size_expected - self.size_begin if self.size_expected >= 0 else -1

	def sizelog(self, size_fetched, size_expected, size_needs, size_curr, spent):
		extra = 'total: {}/fetched: {}'.format(statistics.fbytes(size_expected), statistics.fbytes(size_fetched))
		if size_expected < 0 or size_curr == size_expected:
			log('DEBUG' if size_fetched / spent > 512000 else 'INFO', '{} fetching entirely finished, spent {} secs from {}, {}', self.file_path, statistics.ftimedelta(spent), self.url, extra)
		else:
			if size_needs > 0: extra += '/need: {}'.format(statistics.fbytes(size_needs))
			extra += '/current: {}'.format(statistics.fbytes(size_curr))
			log('INFO', '{} fetching (resuming) finished spent {} secs from {}, {}', self.file_path, statistics.ftimedelta(spent), self.url, extra)

	def download_directly(self, *, decode_unicode=False):
		size_expected = -1
		size_writen = 0
		with session.get(self.url, stream=True, headers=self.headers) as r:
			r.raise_for_status()
			if 'Content-Length' in r.headers: size_expected = int(r.headers['Content-Length'])
			size_writen = 0
			with open(self.file_path, 'w' if decode_unicode else 'wb') as f:
				for chunk in r.iter_content(decode_unicode = decode_unicode, chunk_size=9612):
					if chunk:
						size_writen += f.write(chunk) # chunk.decode("utf-8")
		if size_expected > 0 and size_writen != size_expected: log('ERROR', '{} size {} not match expected {} from {}', self.file_path, size_writen, size_expected, self.url)
		return size_writen

	def download(self, size_expected, size_begin): # return bytes from http
		bytes = 0
		retried = 0
		size_curr = size_begin
		while retried < 5:
			try:
				if (size_expected < 0): 
					bytes = self.download_directly()
					# zzx = self.download_directly()
					# self.url = self.url.replace('/largeb/', '/large/')
					# self.file_path = self.file_path.replace('[zzx]', '')
					# zzx0 = self.download_directly()
					# return zzx0 if zzx0 > 0 else zzx
					break
				while size_curr < size_expected:
					if (size_expected >= 0):
						if size_curr == 0:
							log('DEBUG', "%s total %s to be fetched..." % (self.file_path, statistics.fbytes(size_expected)))
						else:
							log('INFO', "%s total %s and existed %s, resuming from %2.2f%%..." % (self.file_path, statistics.fbytes(size_expected), statistics.fbytes(size_curr), 100 * size_curr / size_expected))
					if (size_curr > 0): self.headers['Range'] = 'bytes=%d-' % size_curr
					with session.get(self.url, stream=True, headers=self.headers) as r:
						r.raise_for_status()
						# for chunk in r.iter_content(chunk_size=9612):
						# 	bytes += len(chunk)
						with open(self.file_path, "ab") as f:
							shutil.copyfileobj(r.raw, f)
					size_curr = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
					bytes = size_curr - size_begin
				break
			except Exception as e:
				log('ERROR', '{} fetching failed error {} retried {}, total {} and fetched {} bytes from {}.', self.file_path, e, retried, size_expected, bytes, self.url)
				retried += 1
		if os.path.exists(self.file_path):
			os.utime(self.file_path, (int(self.created.timestamp()), int(self.created.timestamp())))
		# log('ERROR', '{} fetching failed after full retried {}, total {} and fetched {} bytes from {}.', self.file_path, retried, size_expected, bytes, self.url)
		return bytes

	def start(self):
		if self.size_needs == 0: return 0
		now = timer()
		size_fetched = self.download(self.size_expected, self.size_begin)
		spent = timer() - now
		size_curr = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
		# size_fetched = size_curr - self.size_begin
		self.sizelog(size_fetched, self.size_expected, self.size_needs, size_curr, spent)
		return size_fetched
