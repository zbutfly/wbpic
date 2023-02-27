import time, math, datetime, humanize
from timeit import default_timer as timer
# from hurry.filesize import models.fbytes

BYTE_NAMES = (("B", 1),
	("KB", math.pow(1024, 1)),
	("MB", math.pow(1024, 2)),
	("GB", math.pow(1024, 3)),
	("TB", math.pow(1024, 4)),
	("PB", math.pow(1024, 5)),
	("EB", math.pow(1024, 6)),
	("ZB", math.pow(1024, 7)),
	("YB", math.pow(1024, 8))
)

def roundreserve(x, n):
	i = math.log10(x)
	r = round(x, -int(math.floor(i)) + (n - 1))
	return int(r) if i >= n - 1 else r
	# i = int(math.log10(x))
	# r = n - i
	# if x >= 1: r -= 1
	# r = math.pow(10, r)
	# r = round(x * r) / r
	# return int(r) if i >= n - 1 else r


def fbytes(bytes):
	if bytes == 0:
		return "0B"
	if bytes < 0:
		return "-1"
	i = int(math.floor(math.log(bytes, 1024)))
	n = BYTE_NAMES[i]
	# p = math.pow(1024, i)
	s = roundreserve(bytes / n[1], 3)
	return "%s%s" % (s, n[0])


def ftimedelta(d: datetime.timedelta):
	return humanize.naturaldelta(d, minimum_unit="milliseconds")  #
	# float('%.3g' % ms)


def ftimedelta_t(d: float):  # seconds
	return ftimedelta(datetime.timedelta(seconds=d))


def fspent_t(start: float):  # seconds
	return ftimedelta(datetime.timedelta(seconds=timer() - start))


def fspent(start: datetime.datetime):
	return fspent_t(start.second())


class Statistic(object):

	def __init__(self, *, users: int = 0, mblogs: int = 0, pics_found: int = 0, pics_fetch: int = 0, bytes: int = 0) -> None:
		self.start = datetime.datetime.now()
		self.users = users
		self.mblogs = mblogs
		self.pics_found = pics_found
		self.pics_fetch = pics_fetch
		self.bytes = bytes

	def __add__(self, s: 'Statistic') -> 'Statistic':
		self.users += s.users
		self.mblogs += s.mblogs
		self.pics_found += s.pics_found
		self.pics_fetch += s.pics_fetch
		self.bytes += s.bytes
		return self

	def __radd__(self, s: 'Statistic') -> 'Statistic':
		return self.__add__(self, s)

	def inc(self, *, users: int = 0, mblogs: int = 0, pics_found: int = 0, pics_fetch: int = 0, bytes: int = 0) -> 'Statistic':
		self.users += users
		self.mblogs += mblogs
		self.pics_found += pics_found
		self.pics_fetch += pics_fetch
		self.bytes += bytes
		return self

	__STR_FORMAT__ = "%d users, %d mblogs scaned, %d pics found and %d pics of %s fetched in %s."

	def __str__(self) -> str:
		t = (self.users, self.mblogs, self.pics_found, self.pics_fetch, fbytes(self.bytes), fspent(self.start))
		return Statistic.__STR_FORMAT__ % t


def test():
	s = Statistic(users=9, mblogs=99, pics_found=999, pics_fetch=999, bytes=999999)
	time.sleep(0.3)
	print(s)
	s += Statistic(users=1, mblogs=11, pics_found=111, pics_fetch=111, bytes=111111)
	print(s)
	s.inc(users=1)
	print(s)


if __name__ == '__main__':
	test()
