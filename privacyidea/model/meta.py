# -*- coding: utf-8 -*-
#
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel, info@privacyidea.org
#  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  LSE
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de

"""SQLAlchemy Metadata and Session object"""
from sqlalchemy import MetaData
from sqlalchemy.orm import scoped_session, sessionmaker

__all__ = ['Session', 'engine', 'metadata']

# SQLAlchemy database engine. Updated by model.init_model()
engine = None

# SQLAlchemy session manager. Updated by model.init_model()
Session = scoped_session(sessionmaker(autocommit=False, autoflush=True))

# Global metadata. If you have multiple databases with overlapping table
# names, you'll need a metadata for each database
metadata = MetaData()
