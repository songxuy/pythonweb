#await表明执行协程
import asyncio
import aiomysql
def log(sql,args=()):
	logging.info('SQL:%s' %sql)
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
def execute(sql,args):
	global __pool
	try:
		with (await __pool) as conn:
			cur=await conn.cursor()
			await cur.execute(sql.replace('?','%s'),args)
			affected=cur.rowcount
			await cur.close()
	except BaseException as e:
		raise e
	return affected
def create_args_string(num):
	L=[]
	for n in range(num):
		L.append('?')
	return ', '.join(L)
class Filed(object):
	def __init__(self,name,column_type,primary_key,default):
		self.name=name
		self.column_type=column_type
		self.primary_key=primary_key
		self.default=default
	def __str__(self):#str函数将对象转化为字符砖
		return '<%s,%s:%s>' %(self.__class__.__name__,self.column_type,self.name)
class StringFiled(Filed):
	def __init__(self,name=None,primary_key=False,default=None,ddl='varchar(100)'):
		super().__init__(name,ddl,primary_key,default)
class BoooleanFiled(Filed):
	def __init__(self,name=None,,default=False):
		super().__init__(name,'boolean',False,default)
class IntegerFiled(Filed):
	def __init__(self,name=None,primary_key=False,default=0):
		super().__init__(name,'bigint',primary_key,default)
class FloatFiled(Filed):
	def __init__(self,name=None,primary_key=False,default=0.0):
		super().__init__(name,'real',primary_key,default)
class TextFiled(Filed):
	def __init__(self,name=None,default=None):
		super().__init__(name,'text',False,default)
class ModelMetaClass(type):
    # 元类必须实现__new__方法，当一个类指定通过某元类来创建，那么就会调用该元类的__new__方法
    # 该方法接收4个参数
    # cls为当前准备创建的类的对象 
    # name为类的名字，创建User类，则name便是User
    # bases类继承的父类集合,创建User类，则base便是Model
    # attrs为类的属性/方法集合，创建User类，则attrs便是一个包含User类属性的dict
	def __new__(cls,name,bases,attrs): 
    # 因为Model类是基类，所以排除掉，如果你print(name)的话，会依次打印出Model,User,Blog，即
    # 所有的Model子类，因为这些子类通过Model间接继承元类
    	if name=="Model":
        	return type.__new__(cls,name,bases,attrs)
    # 取出表名，默认与类的名字相同
    	tableName=attrs.get('__table__',None) or name
    	logging.info('found model: %s (table: %s)' % (name, tableName))
    # 用于存储所有的字段，以及字段值
    	mappings=dict()
    # 仅用来存储非主键意外的其它字段，而且只存key
    	fields=[]
    # 仅保存主键的key
    	primaryKey=None
    # 注意这里attrs的key是字段名，value是字段实例，不是字段的具体值
    # 比如User类的id=StringField(...) 这个value就是这个StringField的一个实例，而不是实例化
    # 的时候传进去的具体id值
   		for k,v in attrs.items(): 
        # attrs同时还会拿到一些其它系统提供的类属性，我们只处理自定义的类属性，所以判断一下
        # isinstance 方法用于判断v是否是一个Field 
        	if isinstance(v,Field):
            	mappings[k]=v
            	if v.primary_key:
                	if primaryKey:
                    	raise RuntimeError("Douplicate primary key for field :%s" % key)
                	primaryKey=k
            	else:
                	fields.append(k)
    # 保证了必须有一个主键
    	if not primaryKey:
        	raise RuntimeError("Primary key not found")
    # 这里的目的是去除类属性，为什么要去除呢，因为我想知道的信息已经记录下来了。
    # 去除之后，就访问不到类属性了，如图
        for k in  mappings.keys():
        	attrs.pop(k)
        escaped_fields=list(map(lambda f:'%s' % f,fields))
        attrs['__mappings__'] = mappings # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey # 主键属性名
        attrs['__fields__'] = fields # 除主键外的属性名
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)
class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        ' find number by select and where. '
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    @classmethod
    async def find(cls, pk):
        ' find object by primary key. '
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)





