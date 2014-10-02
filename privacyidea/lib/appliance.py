import os
from subprocess import call
import ConfigParser
import StringIO
import re
import sys
from privacyidea.lib.ext import nginxparser
from privacyidea.lib.freeradiusparser import ClientConfParser
import crypt
import random
import fileinput
import socket
from subprocess import Popen, PIPE
from privacyidea.lib.util import generate_password

DATABASE = "privacyidea"
DBUSER = "privacyidea"
POOL = "./0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


class PrivacyIDEAConfig(object):
    
    ini_template = """[DEFAULT]
debug = false
profile = false
smtp_server = localhost
error_email_from = paste@localhost
privacyideaAudit.type = privacyidea.lib.auditmodules.sqlaudit
privacyideaAudit.key.private = %(here)s/private.pem
privacyideaAudit.key.public = %(here)s/public.pem
privacyideaAudit.sql.highwatermark = 10000
privacyideaGetotp.active = False
privacyideaSecretFile = %(here)s/encKey
privacyideaSuperuserFile = %(here)s/admin-users
privacyideaSuperuserRealms = superuser, 2ndsuperusers
privacyIDEASessionTimeout = 1200
privacyideaURL = https://localhost
privacyideaURL.disable_ssl = False
radius.dictfile = %(here)s/dictionary
radius.nas_identifier = privacyIDEA
privacyideaMachine.applications = privacyidea.lib.applications.ssh, privacyidea.lib.applications.luks

[server:main]
use = egg:Paste#http
host = 0.0.0.0
port = 5001

[app:main]
use = egg:privacyIDEA
sqlalchemy.url = sqlite:///%(here)s/token.sqlite
sqlalchemy.pool_recycle = 3600
full_stack = true
static_files = true
who.log_level = debug
who.log_file = %(here)s/privacyidea.log
cache_dir = %(here)s/data
custom_templates = %(here)s/custom-templates/

[loggers]
keys = root, privacyidea, sqlalchemy

[logger_root]
level = WARNING
handlers = file

[logger_privacyidea]
level = INFO
handlers = file
qualname = privacyidea

[logger_sqlalchemy]
level = ERROR
handlers = file
qualname = sqlalchemy.engine

[handlers]
keys = file

[handler_file]
class = handlers.RotatingFileHandler
args = ('/var/log/privacyidea/privacyidea.log','a', 10000000, 4)
level = INFO
formatter = generic

[formatters]
keys = generic

[formatter_generic]
class = privacyidea.lib.log.SecureFormatter
format = %(asctime)s %(levelname)-5.5s {%(thread)d} [%(name)s][%(funcName)s #%(lineno)d] %(message)s
datefmt = %Y/%m/%d - %H:%M:%S
"""
    
    def __init__(self,
                 file="/etc/privacyidea/privacyidea.ini",
                 init=False):
        self.file = file
        self.raw_config = ConfigParser.RawConfigParser()
        self.raw_config.optionxform = str
        if init:
            self.raw_config.readfp(StringIO.StringIO(self.ini_template))
        else:
            self.raw_config.read(self.file)
            
        self.config = ConfigParser.ConfigParser()
        self.config.optionxform = str
        if init:
            self.config.readfp(StringIO.StringIO(self.ini_template))
        else:
            self.config.read(self.file)
            
        config_path = os.path.abspath(os.path.dirname(self.file))
        self.config.set("DEFAULT", "here", config_path)

    def initialize(self):
        '''
        Initialize the ini file
        '''
        self.raw_config.readfp(StringIO.StringIO(self.ini_template))
    
    def get_getotp(self):
        getotp = self.raw_config.get("DEFAULT", "privacyideaGetotp.active")
        # might be bool or string
        if type(getotp) == bool:
            return getotp
        return getotp.upper() == "TRUE"
    
    def set_getotp(self, bAllow=False):
        self.raw_config.set("DEFAULT", "privacyideaGetotp.active", bAllow)
    
    def get_keyfile(self):
        return self.raw_config.get("DEFAULT", "privacyideaSecretFile")

    def get_adminfile(self):
        return self.raw_config.get("DEFAULT", "privacyideaSuperuserFile")

    def set_adminfile(self, afile):
        self.raw_config.set("DEFAULT", "privacyideaSuperuserFile", afile)
        
    def get_admins(self):
        '''
        return a list of admins
        '''
        admins = []
        admin_file = self.config.get("DEFAULT", "privacyideaSuperuserFile")
        
        try:
            f = open(admin_file, "r")
        except:
            f = None
        
        if f:
            for line in f:
                try:
                    admins.append((line.split(":")[0], line.split(":")[4]))
                except IndexError:
                    pass
            f.close()
        
        return admins
        
    def set_admin(self,
                  admin,
                  password,
                  description=""):
        '''
        create a new admin
        '''
        admin_file = self.config.get("DEFAULT", "privacyideaSuperuserFile")
        try:
            f = open(admin_file, "r")
        except:
            f = None
        max_id = 0
        
        if f:
            for line in f:
                try:
                    uid = int(line.split(":")[2])
                    if uid > max_id:
                        max_id = uid
                except IndexError:
                    pass
            f.close()
            
        salt = (POOL[random.randrange(0, len(POOL))]
                + POOL[random.randrange(0, len(POOL))])
        encryptedPW = crypt.crypt(password, salt)
        gid = max_id + 1
        home = ""
        shell = ""
        
        f = open(admin_file, "a")
        f.write("%s:%s:%s:%s:%s:%s:%s" % (admin,
                                          encryptedPW,
                                          gid,
                                          gid,
                                          description,
                                          home,
                                          shell))
        f.close()
        
    def update_admin(self,
                     admin,
                     password,
                     description=""):
        '''
        update an existing admin
        '''
        admin_file = self.config.get("DEFAULT", "privacyideaSuperuserFile")
        for line in fileinput.input(admin_file, inplace=True):
            # admin_in_file, encryptedPW, uid,
            # gid, description_in_file,
            # home, shell
            fields = line.split(":")
            if admin == fields[0]:
                description_in_file = fields[4]
                salt = (POOL[random.randrange(0, len(POOL))]
                        + POOL[random.randrange(0, len(POOL))])
                encryptedPW = crypt.crypt(password, salt)
                if description:
                    description_in_file = description
                print "%s:%s:%s:%s:%s:%s:%s" % (admin,
                                                encryptedPW,
                                                fields[2],
                                                fields[3],
                                                description_in_file,
                                                fields[5],
                                                fields[6])
            else:
                print line,
                        
    def delete_admin(self, admin):
        '''
        delete the administrator
        '''
        admin_file = self.config.get("DEFAULT", "privacyideaSuperuserFile")
        for line in fileinput.input(admin_file, inplace=True):
            admin_in_file = line.split(":")[0]
            if admin == admin_in_file:
                continue
            print line,
    
    def get_adminrealms(self):
        return self.raw_config.get("DEFAULT", "privacyideaSuperuserRealms")

    def set_adminrealms(self, arealms):
        self.raw_config.set("DEFAULT", "privacyideaSuperuserRealms", arealms)

    def get_DB(self):
        return self.raw_config.get("app:main", "sqlalchemy.url")
    
    def get_DB_dict(self):
        res = {}
        connect_string = self.get_DB()
        pattern = "^(.*)://(.*)/(.*)$"
        m = re.match(pattern, connect_string)
        if m:
            hostpart = m.group(2)
            dbtype = m.group(1)
            dbname = m.group(3)
            password = None
            user = None
            hostparts = hostpart.split('@')
            if len(hostparts) == 2:
                host = hostparts[1]
                try:
                    user, password = hostparts[0].split(':')
                except:
                    user = hostparts[0]
                    password = ""
                
            elif len(hostparts) == 1:
                host = hostparts[0]

            return {"host": host,
                    "user": user,
                    "password": password,
                    "type": dbtype,
                    "database": dbname}

        return res
   
    def DB_init(self):
        '''
        run the paster setup-app command
        '''
        print "Running paster setup-up with %s" % self.file
        p = Popen(['paster', 'setup-app', self.file],
                  stdin=PIPE,
                  stdout=PIPE,
                  stderr=PIPE)
        output, err = p.communicate()
        r = p.returncode
        if r == 0:
            print "Created database tables"
            return True, output
        
        return False, output + "\n" + err
    
    def DB_create(self, database=DATABASE, user=DBUSER):
        '''
        Create the database locally and setup the user.
        
        execute the commands:
        mysqladmin --defaults-file=/etc/mysql/debian.cnf create TEST
        echo  'grant all privileges on TEST.* to "p"@"localhost" \
               identified by "test";'  | mysql \
               --defaults-file=/etc/mysql/debian.cnf
 
        :return (database, user, password): returns the tuple of the
                                  database name,
                                  the username and the password.
        '''
        password = generate_password(size=30)
        dbconfig = (database, user, password)
        
        p = Popen(["mysqladmin",
                   "--defaults-file=/etc/mysql/debian.cnf",
                   "create",
                   database],
                  stdin=PIPE,
                  stdout=PIPE,
                  stderr=PIPE)
        
        _output, err = p.communicate()
        r = p.returncode
        if r != 0 and "database exists" not in err:
            return False, ("%s, %s" % (err, r))
              
        p = Popen(["mysql",
                   "--defaults-file=/etc/mysql/debian.cnf"],
                  stdin=PIPE,
                  stdout=PIPE,
                  stderr=PIPE)
        
        _output, err = p.communicate(input='grant all privileges on %s.* to '
                                           '"%s"@"localhost" '
                                           'identified by "%s";' % (database,
                                                                    user,
                                                                    password),)
        r = p.returncode
        if r != 0:
            return False, (err)
        
        return True, (dbconfig)
        
    def set_DB(self, db_config):
        """
        :param db_config: sets the database parameters (type, host, user,
                          password, database)
        :type db_config: dictionary
        """
        db_str = self.raw_config.get("app:main", "sqlalchemy.url")
        if not db_str:
            db_str = "mysql://privacyidea:privacyidea@localhost/privacyidea"
        print db_config
        # compile hostname
        DB_dict = self.get_DB_dict()
        host = DB_dict.get("host")
        user = DB_dict.get("user")
        dbtype = DB_dict.get("type")
        dbname = DB_dict.get("database")
        password = DB_dict.get("password")

        if db_config.get("type"):
            dbtype = db_config.get("type")
        if db_config.get("database"):
            dbname = db_config.get("database")
        if db_config.get("password") is not None:
            password = db_config.get("password")
        if db_config.get("user") is not None:
            user = db_config.get("user")
        if db_config.get("host"):
            host = db_config.get("host")
            
        if password:
            hostpart = "%s:%s@%s" % (user, password, host)
        elif user:
            hostpart = "%s@%s" % (user, host)
        else:
            hostpart = host
        db_str = "%s://%s/%s" % (dbtype, hostpart, dbname)
            
        self.raw_config.set("app:main", "sqlalchemy.url", db_str)
     
    def get_loglevel(self):
        return self.raw_config.get("handler_file", "level")
    
    def set_loglevel(self, level):
        self.raw_config.set("handler_file", "level", level)
        
    def toggle_getotp(self):
        getotp = self.get_getotp()
        self.raw_config.set("DEFAULT", "privacyideaGetotp.active", not getotp)
        
    def create_audit_keys(self):
        # We can not use the RawConfigParser, since it does not
        # replace the (here)s statement
        private = self.config.get("DEFAULT", "privacyideaAudit.key.private")
        public = self.config.get('DEFAULT', "privacyideaAudit.key.public")

        print "Create private key %s" % private
        r = call("openssl genrsa -out %s 2048" % private,
                 shell=True)
        if r == 0:
            print "create private key: %s" % private

        print "Create public key %s" % public
        r = call("openssl rsa -in %s -pubout -out %s" % (private, public),
                 shell=True)
        if r == 0:
            print "written public key: %s" % private
            return True, private
        
        return False, private
    
    def create_encryption_key(self):
        # We can not use the RawConfigParser, since it does not
        # replace the (here)s statement
        enckey = self.config.get('DEFAULT', "privacyideaSecretFile")

        r = call("dd if=/dev/urandom of='%s' bs=1 count=96" % enckey,
                 shell=True)
        if r == 0:
            print "written enckey: %s" % enckey
            return True, enckey
        return False, enckey

    def save(self):
        with open(self.file, 'wb') as configfile:
            self.raw_config.write(configfile)
        print "Config file %s saved." % self.file


class NginxConfig(object):
    
    NGINX = 0
    UWSGI = 1
    default_file = ["privacyidea", "privacyidea.xml"]
    default_dir_enabled = ["/etc/nginx/sites-enabled",
                           "/etc/uwsgi/apps-enabled"]
    default_dir_available = ["/etc/nginx/sites-available",
                             "/etc/uwsgi/apps-available"]
    
    def __init__(self, files=None):
        '''
        :param files: The default config files for nginx and uwsgi
        :type files: list of two files
        '''
        if files is None:
            files = self.default_file
        self.configfile = files

    def is_active(self):
        '''
        :return: A list of boolean indicating if nginx and uwsgi are active
        '''
        r1 = os.path.isfile(self.default_dir_enabled[0] + "/" +
                            self.configfile[0])
        r2 = os.path.isfile(self.default_dir_enabled[1] + "/" +
                            self.configfile[1])
        return r1, r2
    
    def get(self):
        config = nginxparser.load(open(self.default_dir_available[self.NGINX]
                                       + "/" +
                                       self.configfile[self.NGINX]))
        return config
    
    def enable(self):
        for i in [self.NGINX, self.UWSGI]:
            if not os.path.exists(self.default_dir_enabled[i]):
                os.mkdir(self.default_dir_enabled[i])

            if not os.path.exists(self.default_dir_enabled[i] +
                                  "/" + self.configfile[i]):
                os.symlink(self.default_dir_available[i] +
                           "/" + self.configfile[i],
                           self.default_dir_enabled[i] +
                           "/" + self.configfile[i])
        return
    
    def enable_webservice(self, webservices):
        """
        :param webservices: list of activated links
        :type webservices: list
        """
        if not os.path.exists(self.default_dir_enabled[self.NGINX]):
            os.mkdir(self.default_dir_enabled[self.NGINX])

        active_list = os.listdir(self.default_dir_enabled[self.NGINX])
        # deactivate services
        for service in active_list:
            if service not in webservices:
                # disable webservice
                os.unlink(self.default_dir_enabled[self.NGINX] +
                          "/" + service)
        # activate services
        for service in webservices:
            # enable webservice
            if not os.path.exists(self.default_dir_enabled[self.NGINX] +
                                  "/" + service):
                os.symlink(self.default_dir_available[self.NGINX] +
                           "/" + service,
                           self.default_dir_enabled[self.NGINX] +
                           "/" + service)
    
    def get_webservices(self):
        '''
        returns the contents of /etc/nginx/sites-available
        '''
        ret = []
        file_list = os.listdir(self.default_dir_available[self.NGINX])
        active_list = os.listdir(self.default_dir_enabled[self.NGINX])
        for k in file_list:
            if k in active_list:
                ret.append((k, "", 1))
            else:
                ret.append((k, "", 0))
        return ret
    
    def disable(self):
        for i in [self.NGINX, self.UWSGI]:
            os.unlink(self.default_dir_enabled[i] + "/" + self.configfile[i])
        return
    
    def _get_val(self, data, key):
        '''
        returns a value for a given key from a list of tuples.
        '''
        for kv in data:
            if kv[0] == key:
                return kv[1]
        return
    
    def get_certificates(self):
        '''
        return a tuple of the certificate and the private key
        '''
        config = self.get()
        cert = None
        key = None
        for server in config:
            if server[0] == ["server"]:
                # server config
                if self._get_val(server[1], "listen")[-3:].lower() == "ssl":
                    # the ssl config
                    cert = self._get_val(server[1], "ssl_certificate")
                    key = self._get_val(server[1], "ssl_certificate_key")
        return cert, key
    
    def create_certificates(self):
        certificates = self.get_certificates()
        hostname = socket.getfqdn()
        print("Generating SSL certificate %s and key %s" % certificates)
        if certificates[0] and certificates[1]:
            command = ("openssl req -x509 -newkey rsa:2048 -keyout %s -out"
                       " %s -days 1000 -subj /CN=%s -nodes" %
                       (certificates[1],
                        certificates[0],
                        hostname))
            r = call(command, shell=True)
            if r == 0:
                print "Created the certificate and the key."
                os.chmod(certificates[1], 0x400)
            else:
                print "Failed to create key and certificate: %i" % r
                sys.exit(r)
                
    def restart(self,
                service,
                do_print=False):
        '''
        Restart the nginx and uwsgi
        '''
        p = Popen(['service',
                   service,
                   'restart'],
                  stdin=PIPE,
                  stdout=PIPE,
                  stderr=PIPE)
        _output, _err = p.communicate()
        r = p.returncode
        if r == 0:
            if do_print:
                print "Service %s restarted" % service
        else:
            if do_print:
                print _err


class FreeRADIUSConfig(object):
       
    def __init__(self, client="/etc/freeradius/clients.conf"):
        '''
        Clients are always kept persistent on the file system
        :param client: clients.conf file.
        '''
        # clients
        self.ccp = ClientConfParser(infile=client)
        self.config_path = os.path.dirname(client)
        self.dir_enabled = self.config_path + "/sites-enabled"
        self.dir_available = self.config_path + "/sites-available"
        
    def clients_get(self):
        clients = self.ccp.get_dict()
        return clients
    
    def client_add(self, client=None):
        '''
        :param client: dictionary with a key as the client name and attributes
        :type client: dict
        '''
        if client:
            clients = self.clients_get()
            for client, attributes in client.iteritems():
                clients[client] = attributes
            
            self.ccp.save(clients)
        
    def client_delete(self, clientname=None):
        '''
        :param clientname: name of the client to be deleted
        :type clientname: string
        '''
        if clientname:
            clients = self.clients_get()
            clients.pop(clientname, None)
            self.ccp.save(clients)

    def set_module_perl(self):
        '''
        Set the perl module
        '''
        f = open(self.config_path + "/modules/perl", "w")
        f.write("""perl {
        module = /usr/share/privacyidea/freeradius/privacyidea_radius.pm
}
        """)
        
    def enable_sites(self, sites):
        """
        :param sites: list of activated links
        :type sitess: list
        """
        if not os.path.exists(self.dir_enabled):
            os.mkdir(self.dir_enabled)

        active_list = os.listdir(self.dir_enabled)
        # deactivate site
        for site in active_list:
            if site not in sites:
                # disable site
                os.unlink(self.dir_enabled +
                          "/" + site)
        # activate site
        for site in sites:
            # enable site
            if not os.path.exists(self.dir_enabled +
                                  "/" + site):
                os.symlink(self.dir_available +
                           "/" + site,
                           self.dir_enabled +
                           "/" + site)
    
    def get_sites(self):
        '''
        returns the contents of /etc/freeradius/sites-available
        '''
        ret = []
        file_list = os.listdir(self.dir_available)
        active_list = os.listdir(self.dir_enabled)
        for k in file_list:
            if k in active_list:
                ret.append((k, "", 1))
            else:
                ret.append((k, "", 0))
        return ret
        
#
#  users:
#     DEFAULT Auth-Type := perl
#
#
#
