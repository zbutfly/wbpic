import sys, multiprocessing as mproc, json, wb.context as ctx
from wb.parser import listuser_imap, listuser, listmblogbid, follows
from wb.utils import log, parsesince, parseuids, bsize, sigign


def followings():
	print(json.dumps(follows(), indent=2, ensure_ascii=False))

def wbpic(pool, parals):
	batchsize = int(ctx.opts.get('batchsize_user', '50'))
	if len(sys.argv) == 2 and sys.argv[1].startswith('#'): ctx.sum_pics = listmblogbid(sys.argv[1][1:])
	else:
		since = parsesince()
		uids = parseuids(sys.argv[2:], lambda n: n[0] == '[' and n[1] != '#')
		total = len(uids)
		c = 0
		user_args = []
		for uid in uids:
			c += 1
			if ('skip' in ctx.opts and c <= ctx.opts['skip']): continue
			if not pool: ctx.sum_pics += listuser(uid, since, '[{}/{}]'.format(c, total), uids[uid] if isinstance(uids, dict) else None)
			else:
				user_args += [(uid, since, '[{}/{}]'.format(c, total), uids[uid] if isinstance(uids, dict) else None)]
				if (len(user_args) > batchsize):
					for r in pool.imap_unordered(listuser_imap, user_args):
						ctx.sum_pics += r
					user_args = []

def wbpic1():
	wbpic(None, 1)

def main():
	try:
		ctx.poolize(wbpic1, wbpic)
	finally:
		log('INFO', 'Parsing finished {} pictures found and {} fetched.', ctx.sum_pics, bsize(ctx.sum_bytes))

if __name__ == '__main__': main()