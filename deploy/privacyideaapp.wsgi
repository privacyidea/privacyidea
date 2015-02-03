import sys
sys.path.insert(0, '/home/cornelius/src/privacyidea')
sys.stdout = sys.stderr
from privacyidea.app import create_app
# Now we can select the config file:
application = create_app(config_name="production", config_file="/etc/privacyidea/pi.cfg")
