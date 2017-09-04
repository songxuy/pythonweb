#await表明执行协程
import asyncio
import aiomysql
async def create_pool(**kw):
	logging.info('create ddatabase connection pool...')
	global __pool
	__pool=yield from aiomysql.create_pool(
		host=kw.get('host','localhost'),
		port=kw.get('port',3306),
		user=kw['user'],
		password=kw['password'],
		db=kw['db'],
		charset=kw.get('charset','utf8'),
		autocommit=kw.get('autocommit',True),
		maxsize=kw.get('maxsize',10),
		minsize=kw.get('minsize',1),
		loop=loop

	)
async def select(sql,args,size=None):
	global __pool
	with (await __pool) as conn:
		cur=await conn.cursor(aiomysql.DictCursor)
		await cur.execute(sql.replace('?','%s'),args)
		if size:
			rs=await cur.fetchmany(size)
		else:
			rs=await cur.fetchall()
		await cur.close()
		logging.info('rows returned: %s' % len(rs))
        return rs