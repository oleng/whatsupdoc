#!/usr/bin/env python
""""
[MotherBot] Syntax/docbot : SQLAlchemy database definition /u/num8lock
version:    v.0.2
git:   

"""
import os
import logging, logging.config
import ast
from sqlalchemy import create_engine, func
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, synonym
from datetime import date, datetime

log = logging.getLogger(__name__)
# load logging config from env variable
logging.config.dictConfig(ast.literal_eval(os.getenv('LOG_CFG')))
db_config = os.getenv('DATABASE_URL')
engine = create_engine(db_config, echo=True, isolation_level="READ COMMITTED")

Base = declarative_base()
 
########################################################################
class Library(Base):
    """PostgreSQL table for Python doc definitions"""
    __tablename__ = "Library"
 
    id              = Column(Integer, primary_key=True)
    version_id      = Column(Integer, nullable=False)
    major           = Column(Integer, nullable=False) 
    minor           = Column(Integer, nullable=False) 
    micro           = Column(Integer, nullable=False)
    topic           = Column(String(25), nullable=False)
    module          = Column(String(25), nullable=False)
    keytype         = Column(String(50))
    keyclass        = Column(String(50))
    keywords        = Column(String, nullable=False)
    header          = Column(String, nullable=False)
    body            = Column(String, nullable=False)
    footer          = Column(String, nullable=False)
    url             = Column(String(125))


########################################################################

########################################################################

class RedditActivity(Base):
    """PostgresQL table for Reddit activity record"""
    __tablename__ = "RedditActivity"
    
    id              = Column(Integer, primary_key=True)
    comment_id      = Column(String(25), nullable=False)
    username        = Column(String(100), nullable=False)
    created_utc     = Column(DateTime, default=datetime.utcnow)
    query_keyword   = Column(String, nullable=False)
    query_version   = Column(Integer)
    comment_data    = Column(String)    # permalink, submission_id
    replied         = Column(String(10))
    repliedtime     = Column(DateTime, default=datetime.utcnow)

########################################################################
 
# create tables
Base.metadata.create_all(engine)


