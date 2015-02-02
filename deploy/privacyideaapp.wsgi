import sys
sys.path.insert(0, '/home/cornelius/src/privacyidea')
sys.stdout = sys.stderr
from privacyidea.app import wsgi_app as application
