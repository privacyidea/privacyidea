import sys
sys.stdout = sys.stderr
from privacyidea.app import create_app
# Now we can select the config file:
application = create_app(config_name="production", config_file="/etc/privacyidea/pi.cfg")

from werkzeug.contrib.profiler import ProfilerMiddleware
application.config['PROFILE'] = True
application.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30],
                               profile_dir="/etc/privacyidea")

