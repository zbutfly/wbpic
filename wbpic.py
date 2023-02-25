import sys, json, wb.context as ctx
from timeit import default_timer as timer
from wb.parser import listuser, listmblogbid, follows
from wb.utils import log, parsesince, parseuids, bsize, msec


def followings():
	print(json.dumps(follows(), indent=2, ensure_ascii=False))

def wbpic():
	batchsize = int(ctx.opts.get('batchsize_user', '50'))
	since = parsesince()
	uids = parseuids(sys.argv[2:], lambda n: n[0] == '[' and n[1] != '#')
	total = len(uids)
	c = 0
	user_args = []
	for uid in uids:
		c += 1
		if ('skip' in ctx.opts and c <= ctx.opts['skip']): continue
		user_args += [(uid, since, '[{}/{}]'.format(c, total), uids[uid] if isinstance(uids, dict) else None)]
		if (len(user_args) > batchsize):
			ctx.sum_pics += ctx.poolize(user_args, lambda r:listuser(r[0], r[1], r[2], dir=r[3]))
			user_args = []
	if (len(user_args) > 0):
		ctx.sum_pics += ctx.poolize(user_args, lambda r:listuser(r[0], r[1], r[2], dir=r[3]))

def main():
	now = timer()
	try:
		if len(sys.argv) == 2 and sys.argv[1].startswith('#'): ctx.sum_pics = listmblogbid(sys.argv[1][1:])
		else: wbpic()
	finally:
		spent = timer() - now
		log('INFO', 'Parsing finished {} pictures found and {} fetched in {} secs.', ctx.sum_pics, bsize(ctx.sum_bytes), msec(spent))

if __name__ == '__main__': main()