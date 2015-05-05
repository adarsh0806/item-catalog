#
# Database access functions for the Catalog application.
#
"""dboperations - This module contains database access functions for the Catalog application."""

from datetime import datetime
from passlib.hash import pbkdf2_sha256

# Database stuff
from sqlalchemy import create_engine, func
from sqlalchemy.sql import collate
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from database_setup import Base, Category, Item, User, Admin
engine = create_engine('sqlite:///sportinggoods.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# Get a list of all the categories.
def get_categories():
    """Returns a result set of all categories in alphabetical order, case insensitive."""
    return session.query(Category).order_by('name collate NOCASE').all()

# Get a list of the 10 most recent items added.
def get_recent_items():
    """Returns a result set of the ten most recent items added to the database."""
    return session.query(Item).join(Category).filter('category.id==item.category_id').order_by('item.id desc').limit(10).all()

# Get a category.
def get_category(category_id):
    """Returns a result set for a given category ID."""
    try:
        return session.query(Category).filter_by(id = category_id).one()
    except NoResultFound, e:
        return None

# Get the info for all items in a given category.
def get_category_items(category_id):
    """Returns a result set of all the items for a given category ID."""
    return session.query(Item).filter_by(category_id = category_id).order_by('item.name').all()

# Get the info about an item.
def get_item_info(item_id):
    """Returns a result set for a given item ID."""
    try:
        return session.query(Item).filter_by(id = item_id).one()
    except NoResultFound, e:
        return None

# Check if category already exists.
def does_category_exist(newcategoryname):
    """Returns False if a category does not exist, i.e. the category name is not found."""
    try:
        return session.query(Category).filter(func.lower(Category.name) == func.lower(newcategoryname)).one()
    except NoResultFound, e:
        return False

# Create a new category.
def create_new_category(newcategoryname):
    """Creates a new category."""
    newCategory = Category(name = newcategoryname)
    session.add(newCategory)
    session.commit()

# Update the name of a category.
def update_category(category, newcategoryname):
    """Updates the category name."""
    category.name = newcategoryname
    session.add(category)
    session.commit()

# Delete a catetory.
def delete_category(category):
    """Deletes a category."""
    session.delete(category)
    session.commit()

# Delete all the items in a category.
def delete_category_items(category_id):
    """Deletes all items under a given category ID."""
    items = session.query(Item).filter_by(category_id = category_id).all()

    if items:
        for item in items:
            session.delete(item)
            session.commit()

# Create a new item.
def create_new_item(name, description, price, picture, category_id, user_id):
    """Creates a new item."""
    newItem = Item(name = name, price = price, image = picture, description = description, category_id = category_id, user_id = user_id)
    session.add(newItem)
    session.commit()

# Update an item.
def update_item(item, name, description, price, picture, category_id):
    """Updates an item."""
    item.name = name
    item.description = description
    item.price = price
    item.image = picture
    item.category_id = category_id
    item.last_updated = datetime.utcnow()
    session.add(item)
    session.commit()

# Delete an item.
def delete_item(item):
    """Deletes an item."""
    session.delete(item)
    session.commit()

# Get a list of items created by the user.
def get_user_items(user_id):
    """Returns a result set of items created by a given user ID."""
    return session.query(Item).filter_by(user_id = user_id).all()


# User Helper Functions
# Add the user to the database.
def create_user(login_session):
    """Creates a new user in the database."""
    newUser = User(name = login_session['username'], email = login_session['email'], picture = login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email = login_session['email']).one()
    return user.id

# Get a list of all the users that have registered.
def get_users():
    """Returns a result set of all users registered in the database."""
    return session.query(User).order_by('name collate NOCASE').all()

# Get the user's info from the database.
def get_user_info(user_id):
    """Returns a result set of user information for a given user ID."""
    try:
        return session.query(User).filter_by(id = user_id).one()
    except:
        return None

# Get the user ID from the database.
def get_user_id(email):
    """Gets the user ID for a given email."""
    try:
        user = session.query(User).filter_by(email = email).one()
        return user.id
    except:
        return None

# Check if a user exists.
def does_user_exist(user, password):
    """Returns True if a user is found having the given username and password; False if not."""
    try:
        user = session.query(User).filter_by(email=user).one()
        # Check if the password verifies against the hash stored in the database.
        if pbkdf2_sha256.verify(password, user.password):
            return user
        else:
            return False
    except NoResultFound, e:
        return False

# Check if a user is an admin.
def is_user_admin(user_id):
    """Returns True if the logged in user is an Admin; False if not."""
    try:
        return session.query(Admin).filter_by(user_id=user_id).one()
    except NoResultFound, e:
        return False
