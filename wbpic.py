import sys, json, multiprocessing as mproc, multiprocessing.dummy as mp, wb.context as ctx, wb.utils as utils
from wb.parser import listuser_imap, listmblogbid, follows
from wb.utils import log, parsesince, parseuids, bsize

def followings():
	print(json.dumps(follows(), indent=2, ensure_ascii=False))

# signal.signal(signal.SIGINT, signal.SIG_IGN)
paral = ctx.opts.get('concurrency', mproc.cpu_count() - 1)
utils.tpool = mp.Pool(paral)
try:
	if len(sys.argv) == 2 and sys.argv[1].startswith('#'): ctx.sum_pics = listmblogbid(sys.argv[1][1:])
	else:
		since = parsesince()
		uids = parseuids(sys.argv[2:], lambda n: n[0] == '[' and n[1] != '#')
		total = len(uids)
		c = 0
		async_args = []
		for uid in uids:
			c += 1
			if ('skip' in ctx.opts and c <= ctx.opts['skip']): continue
			async_args += [(uid, since, '[{}/{}]'.format(c, total), uids[uid] if isinstance(uids, dict) else None)]
		for r in utils.tpool.imap_unordered(listuser_imap, async_args, chunksize=paral):
			ctx.sum_pics += r
finally:
	utils.tpool.close()
	utils.tpool.join()
	log('INFO', 'Parsing finished {} pictures found and {} fetched.', ctx.sum_pics, bsize(ctx.sum_bytes))