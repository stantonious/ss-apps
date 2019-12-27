""" Hist Plot package """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"
from flask import Flask
import logging
import sys
app = Flask(__name__)

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session, scoped_session, sessionmaker


Base = automap_base()
db_uri = 'postgresql+psycopg2://pi:raspberry@127.0.0.1:5432/ss'

engine = create_engine(db_uri,
                       pool_size=2,
                       echo=False,
                       isolation_level='READ_COMMITTED',
                       pool_recycle=20,
                       pool_pre_ping=True,
                       echo_pool=True)

Base.prepare(engine, reflect=True)

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

Base.query = db_session.query_property()

Inference = Base.classes.inference


from . import routes