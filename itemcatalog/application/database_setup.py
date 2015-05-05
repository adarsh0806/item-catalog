import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
   
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))
    password = Column(String(250))

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
           'email'        : self.email,
           'picture'      : self.picture,
       }

class Admin(Base):
    __tablename__ = 'admin'
   
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)

class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)

    # We add this serialize function to be able to send JSON objects in a serializable format
    @property
    def serialize(self):
        return {
            'name'          : self.name,
            'id'            : self.id,
        }

class Item(Base):
    __tablename__ = 'item'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(1000))
    price = Column(String(8))
    image = Column(String(250))
    date_created = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)

    # We add this serialize function to be able to send JSON objects in a serializable format
    @property
    def serialize(self):
        return {
            'name'          : self.name,
            'id'            : self.id,
            'description'   : self.description,
            'price'         : self.price,
            'image'         : self.image,
            'category_id'   : self.category_id,
        }

#######insert at end of file #######

engine = create_engine('sqlite:///sportinggoods.db')

Base.metadata.create_all(engine)
