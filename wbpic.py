import sys, json, humanize, wb.context as ctx
from timeit import default_timer as timer
from wb.parser import listuser, listmblogid #, follows
from wb.utils import log, parsesince, parseuids, bsize

# def followings():
# 	print(json.dumps(follows(), indent=2, ensure_ascii=False))

def main():
	now = timer()
	try:
		if len(sys.argv) == 2 and sys.argv[1].startswith('#'): ctx.sum_pics = listmblogid(sys.argv[1][1:])
		else:
			since = parsesince()
			uids = parseuids(sys.argv[2:], lambda n: n[0] == '[' and n[1] != '#')
			total = len(uids)
			c = 0
			if isinstance(uids, dict): ctx.DOWN_MODE = ''
			for uid in uids:
				c += 1
				if ('skip' in ctx.opts and c <= ctx.opts['skip']): continue
				listuser(uid, since, '[{}/{}]'.format(c, total), uids[uid] if isinstance(uids, dict) else None)
	finally:
		spent = (timer() - now)
		log('INFO', 'Parsing finished {} pictures found, and {}pics/{} fetched in {}.', ctx.sum_pics, ctx.sum_pics_downloaded, bsize(ctx.sum_bytes), humanize.naturaldelta(spent, minimum_unit='milliseconds'))

if __name__ == '__main__': main()