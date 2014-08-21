#!/usr/bin/env python
# THis is the app to run with uwsgi
import os 
from paste.script.util.logging_config import fileConfig

INIFILE = '/etc/privacyidea/privacyidea.ini'

os.environ['PYTHON_EGG_CACHE'] = '/var/tmp'

fileConfig( INIFILE )
from paste.deploy import loadapp

application = loadapp('config:%s' % INIFILE)
