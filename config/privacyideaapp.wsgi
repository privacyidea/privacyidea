#!/usr/bin/env python
import os, sys
from paste.script.util.logging_config import fileConfig

BASEDIR = os.path.dirname(__file__)
INIFILE = os.path.join(BASEDIR, 'privacyidea.ini')
sys.path.append(BASEDIR)

os.environ['PYTHON_EGG_CACHE'] = '/var/tmp'

fileConfig( INIFILE )
from paste.deploy import loadapp

application = loadapp('config:%s' % INIFILE)
