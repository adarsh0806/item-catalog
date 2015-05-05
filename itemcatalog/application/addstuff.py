from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.hash import pbkdf2_sha256

import json
 
from database_setup import Category, Base, Item, User, Admin
 
engine = create_engine('sqlite:///sportinggoods.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create an Admin user and store the password as a hash.
phash = pbkdf2_sha256.encrypt("mycatalog", rounds=1000, salt_size=16)

user1 = User(name="Admin", email="admin", picture="", password=phash)
session.add(user1)
session.commit()

# set up admin user
admin1 = Admin(user_id=1)
session.add(admin1)
session.commit()

# Read the JSON file and populate the database with categories and items.
itemsFile = open("items.json")

data = json.load(itemsFile)

cnum = len(data['Categories'])  # determines how many categories
for c in range(0, cnum):

    print(data['Categories'][c]['name'])

    category1 = Category(name=data['Categories'][c]['name'])
    session.add(category1)
    session.commit()

    inum = len(data['Categories'][c]['items'])    # determines how many items
    for i in range(0, inum):

        item = Item(name=data['Categories'][c]['items'][i]['name'], description=data['Categories'][c]['items'][i]['description'], price=data['Categories'][c]['items'][i]['price'], image=data['Categories'][c]['items'][i]['picture'], category=category1)
        session.add(item)
        session.commit()

print "Added categories and items!"
