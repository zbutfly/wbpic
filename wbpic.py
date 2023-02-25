import sys, json, wb.context as ctx
from wb.parser import listuser, listmblogbid, follows
from wb.utils import log, parsesince, parseuids, bsize

def followings():
	print(json.dumps(follows(), indent=2, ensure_ascii=False))

def main():
	try:
		if len(sys.argv) == 2 and sys.argv[1].startswith('#'): ctx.sum_pics = listmblogbid(sys.argv[1][1:])
		else:
			since = parsesince()
			uids = parseuids(sys.argv[2:], lambda n: n[0] == '[' and n[1] != '#')
			total = len(uids)
			c = 0
			for uid in uids:
				c += 1
				if ('skip' in ctx.opts and c <= ctx.opts['skip']): continue
				ctx.sum_pics += listuser(uid, since, '[{}/{}]'.format(c, total), uids[uid] if isinstance(uids, dict) else None)
	finally:
		log('INFO', 'Parsing finished {} pictures found and {} fetched.', ctx.sum_pics, bsize(ctx.sum_bytes))

if __name__ == '__main__': main()