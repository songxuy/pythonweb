from pool import create_pool
from model import User,Blog,Comment
def test():
	yield from pool.create_pool(user='root',password='song',database='awepy')
	u=User(name='test',email='test@example.com',passwd='12345678',image='about:black')
	yield from u.save()
for x in test():
	pass
