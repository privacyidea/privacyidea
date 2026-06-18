-- Seed data for migration tests pinned at START_REVISION 5cb310101a1f (v3.9)
-- Dialect: Oracle
--
-- This file represents a realistic privacyIDEA v3.9 database state in native
-- Oracle syntax. It was produced by tools/generate_seed_sql.py (oracle dialect)
-- and then extended with representative INSERT rows and an alembic_version
-- stamp, mirroring the MariaDB/PostgreSQL seeds.
--
-- Oracle-specific notes vs. the PostgreSQL/MariaDB seeds:
--   * Boolean columns compile to SMALLINT, so values are 0/1 (not TRUE/FALSE).
--   * Oracle has no multi-row "VALUES (...),(...)" so each row is its own INSERT.
--   * Datetime literals use the ANSI "TIMESTAMP 'YYYY-MM-DD HH24:MI:SS'" form.
--   * Sequence-backed PKs use "DEFAULT <seq>.nextval" (like Postgres's
--     "DEFAULT nextval(...)"), so the sequences are created BEFORE the tables.
--     Each sequence is baked with START WITH = MAX(id)+1 of the seeded data,
--     matching an upgraded install just after migration 5cb310101a1f created
--     them. Oracle needs neither the Galera "INCREMENT BY 0" nor Postgres
--     "SERIAL" machinery.
--
-- Usage:
--   engine = create_engine(DB_URL)
--   with engine.connect() as conn:
--       for stmt in _read_seed_sql(path):
--           conn.execute(text(stmt))
--       conn.commit()
--   command.stamp(cfg, "5cb310101a1f")

-- ---------------------------------------------------------------------------
-- Sequences (created first because table PKs default to <seq>.nextval)
-- ---------------------------------------------------------------------------
CREATE SEQUENCE authcache_seq START WITH 1;
CREATE SEQUENCE caconnector_seq START WITH 1;
CREATE SEQUENCE challenge_seq START WITH 1;
CREATE SEQUENCE clientapp_seq START WITH 3;
CREATE SEQUENCE eventcounter_seq START WITH 3;
CREATE SEQUENCE eventhandler_seq START WITH 2;
CREATE SEQUENCE machineresolver_seq START WITH 1;
CREATE SEQUENCE monitoringstats_seq START WITH 3;
CREATE SEQUENCE pwreset_seq START WITH 1;
CREATE SEQUENCE periodictask_seq START WITH 2;
CREATE SEQUENCE audit_seq START WITH 3;
CREATE SEQUENCE policy_seq START WITH 5;
CREATE SEQUENCE privacyideaserver_seq START WITH 1;
CREATE SEQUENCE radiusserver_seq START WITH 1;
CREATE SEQUENCE realm_seq START WITH 3;
CREATE SEQUENCE resolver_seq START WITH 2;
CREATE SEQUENCE serviceid_seq START WITH 2;
CREATE SEQUENCE smsgateway_seq START WITH 2;
CREATE SEQUENCE smtpserver_seq START WITH 2;
CREATE SEQUENCE subscription_seq START WITH 1;
CREATE SEQUENCE token_seq START WITH 4;
CREATE SEQUENCE tokengroup_seq START WITH 3;
CREATE SEQUENCE usercache_seq START WITH 1;
CREATE SEQUENCE caconfig_seq START WITH 1;
CREATE SEQUENCE customuserattribute_seq START WITH 2;
CREATE SEQUENCE eventhandlercond_seq START WITH 2;
CREATE SEQUENCE eventhandleropt_seq START WITH 3;
CREATE SEQUENCE machineresolverconf_seq START WITH 1;
CREATE SEQUENCE machinetoken_seq START WITH 1;
CREATE SEQUENCE periodictasklastrun_seq START WITH 2;
CREATE SEQUENCE periodictaskopt_seq START WITH 2;
CREATE SEQUENCE policycondition_seq START WITH 2;
CREATE SEQUENCE resolverconf_seq START WITH 2;
CREATE SEQUENCE resolverrealm_seq START WITH 3;
CREATE SEQUENCE smsgwoption_seq START WITH 3;
CREATE SEQUENCE tokeninfo_seq START WITH 5;
CREATE SEQUENCE tokenowner_seq START WITH 3;
CREATE SEQUENCE tokenrealm_seq START WITH 4;
CREATE SEQUENCE tokentokengroup_seq START WITH 3;
CREATE SEQUENCE machtokenopt_seq START WITH 1;

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------
CREATE TABLE admin (
	username VARCHAR2(120 CHAR) NOT NULL, 
	password VARCHAR2(255 CHAR), 
	email VARCHAR2(255 CHAR), 
	PRIMARY KEY (username)
);

CREATE TABLE authcache (
	id INTEGER DEFAULT authcache_seq.nextval NOT NULL, 
	first_auth DATE, 
	last_auth DATE, 
	username VARCHAR2(64 CHAR), 
	resolver VARCHAR2(120 CHAR), 
	realm VARCHAR2(120 CHAR), 
	client_ip VARCHAR2(40 CHAR), 
	user_agent VARCHAR2(120 CHAR), 
	auth_count INTEGER, 
	authentication VARCHAR2(255 CHAR), 
	PRIMARY KEY (id)
);

CREATE TABLE caconnector (
	id INTEGER DEFAULT caconnector_seq.nextval NOT NULL, 
	name VARCHAR2(255 CHAR) NOT NULL, 
	catype VARCHAR2(255 CHAR) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE challenge (
	id INTEGER DEFAULT challenge_seq.nextval NOT NULL, 
	transaction_id VARCHAR2(64 CHAR) NOT NULL, 
	data VARCHAR2(512 CHAR), 
	challenge VARCHAR2(512 CHAR), 
	"session" VARCHAR2(512 CHAR), 
	serial VARCHAR2(40 CHAR), 
	timestamp DATE, 
	expiration DATE, 
	received_count INTEGER, 
	otp_valid SMALLINT, 
	PRIMARY KEY (id)
);

CREATE TABLE clientapplication (
	id INTEGER DEFAULT clientapp_seq.nextval NOT NULL, 
	ip VARCHAR2(255 CHAR) NOT NULL, 
	hostname VARCHAR2(255 CHAR), 
	clienttype VARCHAR2(255 CHAR) NOT NULL, 
	lastseen DATE, 
	node VARCHAR2(255 CHAR) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT caix UNIQUE (ip, clienttype, node)
);

CREATE TABLE config (
	"Key" VARCHAR2(255 CHAR) NOT NULL, 
	"Value" VARCHAR2(2000 CHAR), 
	"Type" VARCHAR2(2000 CHAR), 
	"Description" VARCHAR2(2000 CHAR), 
	PRIMARY KEY ("Key")
);

CREATE TABLE eventcounter (
	id INTEGER DEFAULT eventcounter_seq.nextval NOT NULL, 
	counter_name VARCHAR2(80 CHAR) NOT NULL, 
	counter_value INTEGER, 
	node VARCHAR2(255 CHAR) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT evctr_1 UNIQUE (counter_name, node)
);

CREATE TABLE eventhandler (
	id INTEGER DEFAULT eventhandler_seq.nextval NOT NULL, 
	name VARCHAR2(64 CHAR), 
	active SMALLINT, 
	ordering INTEGER NOT NULL, 
	position VARCHAR2(10 CHAR), 
	event VARCHAR2(255 CHAR) NOT NULL, 
	handlermodule VARCHAR2(255 CHAR) NOT NULL, 
	condition VARCHAR2(1024 CHAR), 
	action VARCHAR2(1024 CHAR), 
	PRIMARY KEY (id)
);

CREATE TABLE machineresolver (
	id INTEGER DEFAULT machineresolver_seq.nextval NOT NULL, 
	name VARCHAR2(255 CHAR) NOT NULL, 
	rtype VARCHAR2(255 CHAR) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE monitoringstats (
	id INTEGER DEFAULT monitoringstats_seq.nextval NOT NULL, 
	timestamp DATE NOT NULL, 
	stats_key VARCHAR2(128 CHAR) NOT NULL, 
	stats_value INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT msix_1 UNIQUE (timestamp, stats_key)
);

CREATE TABLE passwordreset (
	id INTEGER DEFAULT pwreset_seq.nextval NOT NULL, 
	recoverycode VARCHAR2(255 CHAR) NOT NULL, 
	username VARCHAR2(64 CHAR) NOT NULL, 
	realm VARCHAR2(64 CHAR) NOT NULL, 
	resolver VARCHAR2(64 CHAR), 
	email VARCHAR2(255 CHAR), 
	timestamp DATE, 
	expiration DATE, 
	PRIMARY KEY (id)
);

CREATE TABLE periodictask (
	id INTEGER DEFAULT periodictask_seq.nextval NOT NULL, 
	name VARCHAR2(64 CHAR) NOT NULL, 
	active SMALLINT NOT NULL, 
	retry_if_failed SMALLINT NOT NULL, 
	interval VARCHAR2(256 CHAR) NOT NULL, 
	nodes VARCHAR2(256 CHAR) NOT NULL, 
	taskmodule VARCHAR2(256 CHAR) NOT NULL, 
	ordering INTEGER NOT NULL, 
	last_update DATE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE pidea_audit (
	id INTEGER DEFAULT audit_seq.nextval NOT NULL, 
	"date" DATE, 
	startdate DATE, 
	duration INTERVAL DAY TO SECOND(6), 
	signature VARCHAR2(620 CHAR), 
	action VARCHAR2(50 CHAR), 
	success INTEGER, 
	serial VARCHAR2(40 CHAR), 
	token_type VARCHAR2(12 CHAR), 
	"user" VARCHAR2(20 CHAR), 
	realm VARCHAR2(20 CHAR), 
	resolver VARCHAR2(50 CHAR), 
	administrator VARCHAR2(20 CHAR), 
	action_detail VARCHAR2(50 CHAR), 
	info VARCHAR2(50 CHAR), 
	privacyidea_server VARCHAR2(255 CHAR), 
	client VARCHAR2(50 CHAR), 
	loglevel VARCHAR2(12 CHAR), 
	clearance_level VARCHAR2(12 CHAR), 
	thread_id VARCHAR2(20 CHAR), 
	policies VARCHAR2(255 CHAR), 
	PRIMARY KEY (id)
);

CREATE TABLE policy (
	id INTEGER DEFAULT policy_seq.nextval NOT NULL, 
	active SMALLINT, 
	check_all_resolvers SMALLINT, 
	name VARCHAR2(64 CHAR) NOT NULL, 
	scope VARCHAR2(32 CHAR) NOT NULL, 
	action VARCHAR2(2000 CHAR), 
	realm VARCHAR2(256 CHAR), 
	adminrealm VARCHAR2(256 CHAR), 
	adminuser VARCHAR2(256 CHAR), 
	resolver VARCHAR2(256 CHAR), 
	pinode VARCHAR2(256 CHAR), 
	"user" VARCHAR2(256 CHAR), 
	client VARCHAR2(256 CHAR), 
	time VARCHAR2(64 CHAR), 
	priority INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE privacyideaserver (
	id INTEGER DEFAULT privacyideaserver_seq.nextval NOT NULL, 
	identifier VARCHAR2(255 CHAR) NOT NULL, 
	url VARCHAR2(255 CHAR) NOT NULL, 
	tls SMALLINT, 
	description VARCHAR2(2000 CHAR), 
	PRIMARY KEY (id), 
	UNIQUE (identifier)
);

CREATE TABLE radiusserver (
	id INTEGER DEFAULT radiusserver_seq.nextval NOT NULL, 
	identifier VARCHAR2(255 CHAR) NOT NULL, 
	server VARCHAR2(255 CHAR) NOT NULL, 
	port INTEGER, 
	secret VARCHAR2(255 CHAR), 
	dictionary VARCHAR2(255 CHAR), 
	description VARCHAR2(2000 CHAR), 
	timeout INTEGER, 
	retries INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (identifier)
);

CREATE TABLE realm (
	id INTEGER DEFAULT realm_seq.nextval NOT NULL, 
	name VARCHAR2(255 CHAR) NOT NULL, 
	"default" SMALLINT, 
	"option" VARCHAR2(40 CHAR), 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE resolver (
	id INTEGER DEFAULT resolver_seq.nextval NOT NULL, 
	name VARCHAR2(255 CHAR) NOT NULL, 
	rtype VARCHAR2(255 CHAR) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE serviceid (
	id INTEGER DEFAULT serviceid_seq.nextval NOT NULL, 
	name VARCHAR2(255 CHAR) NOT NULL, 
	"Description" VARCHAR2(2000 CHAR), 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE smsgateway (
	id INTEGER DEFAULT smsgateway_seq.nextval NOT NULL, 
	identifier VARCHAR2(255 CHAR) NOT NULL, 
	description VARCHAR2(1024 CHAR), 
	providermodule VARCHAR2(1024 CHAR) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (identifier)
);

CREATE TABLE smtpserver (
	id INTEGER DEFAULT smtpserver_seq.nextval NOT NULL, 
	identifier VARCHAR2(255 CHAR) NOT NULL, 
	server VARCHAR2(255 CHAR) NOT NULL, 
	port INTEGER, 
	username VARCHAR2(255 CHAR), 
	password VARCHAR2(255 CHAR), 
	sender VARCHAR2(255 CHAR), 
	tls SMALLINT, 
	description VARCHAR2(2000 CHAR), 
	timeout INTEGER, 
	enqueue_job SMALLINT NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE subscription (
	id INTEGER DEFAULT subscription_seq.nextval NOT NULL, 
	application VARCHAR2(80 CHAR), 
	for_name VARCHAR2(80 CHAR) NOT NULL, 
	for_address VARCHAR2(128 CHAR), 
	for_email VARCHAR2(128 CHAR) NOT NULL, 
	for_phone VARCHAR2(50 CHAR) NOT NULL, 
	for_url VARCHAR2(80 CHAR), 
	for_comment VARCHAR2(255 CHAR), 
	by_name VARCHAR2(50 CHAR) NOT NULL, 
	by_email VARCHAR2(128 CHAR) NOT NULL, 
	by_address VARCHAR2(128 CHAR), 
	by_phone VARCHAR2(50 CHAR), 
	by_url VARCHAR2(80 CHAR), 
	date_from DATE, 
	date_till DATE, 
	num_users INTEGER, 
	num_tokens INTEGER, 
	num_clients INTEGER, 
	"level" VARCHAR2(80 CHAR), 
	signature VARCHAR2(640 CHAR), 
	PRIMARY KEY (id)
);

CREATE TABLE token (
	id INTEGER DEFAULT token_seq.nextval NOT NULL, 
	description VARCHAR2(80 CHAR), 
	serial VARCHAR2(40 CHAR) NOT NULL, 
	tokentype VARCHAR2(30 CHAR), 
	user_pin VARCHAR2(512 CHAR), 
	user_pin_iv VARCHAR2(32 CHAR), 
	so_pin VARCHAR2(512 CHAR), 
	so_pin_iv VARCHAR2(32 CHAR), 
	pin_seed VARCHAR2(32 CHAR), 
	otplen INTEGER, 
	pin_hash VARCHAR2(512 CHAR), 
	key_enc VARCHAR2(2800 CHAR), 
	key_iv VARCHAR2(32 CHAR), 
	maxfail INTEGER, 
	active SMALLINT NOT NULL, 
	revoked SMALLINT, 
	locked SMALLINT, 
	failcount INTEGER, 
	count INTEGER, 
	count_window INTEGER, 
	sync_window INTEGER, 
	rollout_state VARCHAR2(10 CHAR), 
	PRIMARY KEY (id)
);

CREATE TABLE tokengroup (
	id INTEGER DEFAULT tokengroup_seq.nextval NOT NULL, 
	name VARCHAR2(255 CHAR) NOT NULL, 
	"Description" VARCHAR2(2000 CHAR), 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE usercache (
	id INTEGER DEFAULT usercache_seq.nextval NOT NULL, 
	username VARCHAR2(64 CHAR), 
	used_login VARCHAR2(64 CHAR), 
	resolver VARCHAR2(120 CHAR), 
	user_id VARCHAR2(320 CHAR), 
	timestamp DATE, 
	PRIMARY KEY (id)
);

CREATE TABLE caconnectorconfig (
	id INTEGER DEFAULT caconfig_seq.nextval NOT NULL, 
	caconnector_id INTEGER, 
	"Key" VARCHAR2(255 CHAR) NOT NULL, 
	"Value" VARCHAR2(2000 CHAR), 
	"Type" VARCHAR2(2000 CHAR), 
	"Description" VARCHAR2(2000 CHAR), 
	PRIMARY KEY (id), 
	CONSTRAINT ccix_2 UNIQUE (caconnector_id, "Key"), 
	FOREIGN KEY(caconnector_id) REFERENCES caconnector (id)
);

CREATE TABLE customuserattribute (
	id INTEGER DEFAULT customuserattribute_seq.nextval NOT NULL, 
	user_id VARCHAR2(320 CHAR), 
	resolver VARCHAR2(120 CHAR), 
	realm_id INTEGER, 
	"Key" VARCHAR2(255 CHAR) NOT NULL, 
	"Value" CLOB, 
	"Type" VARCHAR2(100 CHAR), 
	PRIMARY KEY (id), 
	FOREIGN KEY(realm_id) REFERENCES realm (id)
);

CREATE TABLE eventhandlercondition (
	id INTEGER DEFAULT eventhandlercond_seq.nextval NOT NULL, 
	eventhandler_id INTEGER, 
	"Key" VARCHAR2(255 CHAR) NOT NULL, 
	"Value" VARCHAR2(2000 CHAR), 
	comparator VARCHAR2(255 CHAR), 
	PRIMARY KEY (id), 
	CONSTRAINT ehcix_1 UNIQUE (eventhandler_id, "Key"), 
	FOREIGN KEY(eventhandler_id) REFERENCES eventhandler (id)
);

CREATE TABLE eventhandleroption (
	id INTEGER DEFAULT eventhandleropt_seq.nextval NOT NULL, 
	eventhandler_id INTEGER, 
	"Key" VARCHAR2(255 CHAR) NOT NULL, 
	"Value" VARCHAR2(2000 CHAR), 
	"Type" VARCHAR2(2000 CHAR), 
	"Description" VARCHAR2(2000 CHAR), 
	PRIMARY KEY (id), 
	CONSTRAINT ehoix_1 UNIQUE (eventhandler_id, "Key"), 
	FOREIGN KEY(eventhandler_id) REFERENCES eventhandler (id)
);

CREATE TABLE machineresolverconfig (
	id INTEGER DEFAULT machineresolverconf_seq.nextval NOT NULL, 
	resolver_id INTEGER, 
	"Key" VARCHAR2(255 CHAR) NOT NULL, 
	"Value" VARCHAR2(2000 CHAR), 
	"Type" VARCHAR2(2000 CHAR), 
	"Description" VARCHAR2(2000 CHAR), 
	PRIMARY KEY (id), 
	CONSTRAINT mrcix_2 UNIQUE (resolver_id, "Key"), 
	FOREIGN KEY(resolver_id) REFERENCES machineresolver (id)
);

CREATE TABLE machinetoken (
	id INTEGER DEFAULT machinetoken_seq.nextval NOT NULL, 
	token_id INTEGER, 
	machineresolver_id INTEGER, 
	machine_id VARCHAR2(255 CHAR), 
	application VARCHAR2(64 CHAR), 
	PRIMARY KEY (id), 
	FOREIGN KEY(token_id) REFERENCES token (id)
);

CREATE TABLE periodictasklastrun (
	id INTEGER DEFAULT periodictasklastrun_seq.nextval NOT NULL, 
	periodictask_id INTEGER, 
	node VARCHAR2(255 CHAR) NOT NULL, 
	timestamp DATE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ptlrix_1 UNIQUE (periodictask_id, node), 
	FOREIGN KEY(periodictask_id) REFERENCES periodictask (id)
);

CREATE TABLE periodictaskoption (
	id INTEGER DEFAULT periodictaskopt_seq.nextval NOT NULL, 
	periodictask_id INTEGER, 
	key VARCHAR2(255 CHAR) NOT NULL, 
	value VARCHAR2(2000 CHAR), 
	PRIMARY KEY (id), 
	CONSTRAINT ptoix_1 UNIQUE (periodictask_id, key), 
	FOREIGN KEY(periodictask_id) REFERENCES periodictask (id)
);

CREATE TABLE policycondition (
	id INTEGER DEFAULT policycondition_seq.nextval NOT NULL, 
	policy_id INTEGER NOT NULL, 
	section VARCHAR2(255 CHAR) NOT NULL, 
	"Key" VARCHAR2(255 CHAR) NOT NULL, 
	comparator VARCHAR2(255 CHAR) NOT NULL, 
	"Value" VARCHAR2(2000 CHAR) NOT NULL, 
	active SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(policy_id) REFERENCES policy (id)
);

CREATE TABLE resolverconfig (
	id INTEGER DEFAULT resolverconf_seq.nextval NOT NULL, 
	resolver_id INTEGER, 
	"Key" VARCHAR2(255 CHAR) NOT NULL, 
	"Value" VARCHAR2(2000 CHAR), 
	"Type" VARCHAR2(2000 CHAR), 
	"Description" VARCHAR2(2000 CHAR), 
	PRIMARY KEY (id), 
	CONSTRAINT rcix_2 UNIQUE (resolver_id, "Key"), 
	FOREIGN KEY(resolver_id) REFERENCES resolver (id)
);

CREATE TABLE resolverrealm (
	id INTEGER DEFAULT resolverrealm_seq.nextval NOT NULL, 
	resolver_id INTEGER, 
	realm_id INTEGER, 
	priority INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT rrix_2 UNIQUE (resolver_id, realm_id), 
	FOREIGN KEY(resolver_id) REFERENCES resolver (id), 
	FOREIGN KEY(realm_id) REFERENCES realm (id)
);

CREATE TABLE smsgatewayoption (
	id INTEGER DEFAULT smsgwoption_seq.nextval NOT NULL, 
	"Key" VARCHAR2(255 CHAR) NOT NULL, 
	"Value" CLOB, 
	"Type" VARCHAR2(100 CHAR), 
	gateway_id INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT sgix_1 UNIQUE (gateway_id, "Key", "Type"), 
	FOREIGN KEY(gateway_id) REFERENCES smsgateway (id)
);

CREATE TABLE tokeninfo (
	id INTEGER DEFAULT tokeninfo_seq.nextval NOT NULL, 
	"Key" VARCHAR2(255 CHAR) NOT NULL, 
	"Value" CLOB, 
	"Type" VARCHAR2(100 CHAR), 
	"Description" VARCHAR2(2000 CHAR), 
	token_id INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT tiix_2 UNIQUE (token_id, "Key"), 
	FOREIGN KEY(token_id) REFERENCES token (id)
);

CREATE TABLE tokenowner (
	id INTEGER DEFAULT tokenowner_seq.nextval NOT NULL, 
	token_id INTEGER, 
	resolver VARCHAR2(120 CHAR), 
	user_id VARCHAR2(320 CHAR), 
	realm_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(token_id) REFERENCES token (id), 
	FOREIGN KEY(realm_id) REFERENCES realm (id)
);

CREATE TABLE tokenrealm (
	id INTEGER DEFAULT tokenrealm_seq.nextval, 
	token_id INTEGER, 
	realm_id INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT trix_2 UNIQUE (token_id, realm_id), 
	FOREIGN KEY(token_id) REFERENCES token (id), 
	FOREIGN KEY(realm_id) REFERENCES realm (id)
);

CREATE TABLE tokentokengroup (
	id INTEGER DEFAULT tokentokengroup_seq.nextval, 
	token_id INTEGER, 
	tokengroup_id INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT ttgix_2 UNIQUE (token_id, tokengroup_id), 
	FOREIGN KEY(token_id) REFERENCES token (id), 
	FOREIGN KEY(tokengroup_id) REFERENCES tokengroup (id)
);

CREATE TABLE machinetokenoptions (
	id INTEGER DEFAULT machtokenopt_seq.nextval NOT NULL, 
	machinetoken_id INTEGER, 
	mt_key VARCHAR2(64 CHAR) NOT NULL, 
	mt_value VARCHAR2(64 CHAR) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(machinetoken_id) REFERENCES machinetoken (id)
);

-- ---------------------------------------------------------------------------
-- Data
-- ---------------------------------------------------------------------------
INSERT INTO config ("Key", "Value", "Type", "Description") VALUES ('PI_PEPPER',          'dGVzdHBlcHBlcg==', 'password', 'Pepper for hashing');
INSERT INTO config ("Key", "Value", "Type", "Description") VALUES ('DefaultOtpLen',      '6',                '',         '');
INSERT INTO config ("Key", "Value", "Type", "Description") VALUES ('DefaultMaxFailCount','10',               '',         '');
INSERT INTO config ("Key", "Value", "Type", "Description") VALUES ('__timestamp__',      '1680000000',       '',         'config timestamp. last changed.');
INSERT INTO realm (id, name, "default") VALUES (1, 'defrealm',  1);
INSERT INTO realm (id, name, "default") VALUES (2, 'testrealm', 0);
INSERT INTO resolver (id, name, rtype) VALUES (1, 'defresolver', 'passwdresolver');
INSERT INTO resolverconfig (id, resolver_id, "Key", "Value") VALUES (1, 1, 'fileName', '/etc/passwd');
INSERT INTO resolverrealm (id, resolver_id, realm_id, priority) VALUES (1, 1, 1, 1);
INSERT INTO resolverrealm (id, resolver_id, realm_id, priority) VALUES (2, 1, 2, 1);
INSERT INTO token (id, serial, tokentype, otplen, active, key_enc, key_iv, pin_hash) VALUES (1, 'HOTP0001', 'hotp', 6, 1, 'aabbccddeeff00112233445566778899aabbccddeeff001122334455', '00112233445566778899aabbccdd0011', '$pbkdf2-sha512$...fakehash...');
INSERT INTO token (id, serial, tokentype, otplen, active, key_enc, key_iv, pin_hash) VALUES (2, 'TOTP0001', 'totp', 6, 1, 'aabbccddeeff00112233445566778899aabbccddeeff001122334455', '00112233445566778899aabbccdd0022', '');
INSERT INTO token (id, serial, tokentype, otplen, active, key_enc, key_iv, pin_hash) VALUES (3, 'PIPU0001', 'push', 6, 1, '', '', '');
INSERT INTO tokeninfo (id, token_id, "Key", "Value") VALUES (1, 2, 'timeStep',              '30');
INSERT INTO tokeninfo (id, token_id, "Key", "Value") VALUES (2, 2, 'timeWindow',            '180');
INSERT INTO tokeninfo (id, token_id, "Key", "Value") VALUES (3, 3, 'firebase_config',       'myFirebase');
INSERT INTO tokeninfo (id, token_id, "Key", "Value") VALUES (4, 3, 'public_key_smartphone', 'fakePublicKey==');
INSERT INTO tokenowner (id, token_id, resolver, user_id, realm_id) VALUES (1, 1, 'defresolver', '1000', 1);
INSERT INTO tokenowner (id, token_id, resolver, user_id, realm_id) VALUES (2, 2, 'defresolver', '1000', 1);
INSERT INTO tokenrealm (id, token_id, realm_id) VALUES (1, 1, 1);
INSERT INTO tokenrealm (id, token_id, realm_id) VALUES (2, 2, 1);
INSERT INTO tokenrealm (id, token_id, realm_id) VALUES (3, 3, 1);
INSERT INTO tokengroup (id, name, "Description") VALUES (1, 'vpn-tokens',   'Tokens used for VPN access');
INSERT INTO tokengroup (id, name, "Description") VALUES (2, 'admin-tokens', 'Tokens for administrators');
INSERT INTO tokentokengroup (id, token_id, tokengroup_id) VALUES (1, 1, 1);
INSERT INTO tokentokengroup (id, token_id, tokengroup_id) VALUES (2, 2, 2);
INSERT INTO policy (id, active, name, scope, action, realm, priority) VALUES (1, 1,  'superuser',         'admin',  'superuser',         '',        1);
INSERT INTO policy (id, active, name, scope, action, realm, priority) VALUES (2, 1,  'enroll-hotp',       'enroll', 'enrollHOTP',        'defrealm',1);
INSERT INTO policy (id, active, name, scope, action, realm, priority) VALUES (3, 1,  'no-detail-on-fail', 'authz',  'no_detail_on_fail', '',        1);
INSERT INTO policy (id, active, name, scope, action, realm, priority) VALUES (4, 0, 'disabled-policy',   'auth',   'push_wait=20',      '',        1);
INSERT INTO policycondition (id, policy_id, section, "Key", comparator, "Value", active) VALUES (1, 2, 'userinfo', 'memberOf', 'equals', 'cn=vpn,dc=example,dc=com', 1);
INSERT INTO admin (username, password, email) VALUES ('admin', '$pbkdf2-sha512$25000$fakesalt$fakehash==', 'admin@example.com');
INSERT INTO smsgateway (id, identifier, description, providermodule) VALUES (1, 'myFirebase', 'Firebase push gateway', 'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider');
INSERT INTO smsgatewayoption (id, gateway_id, "Key", "Value", "Type") VALUES (1, 1, 'FIREBASE_CONFIG', '/etc/privacyidea/firebase.json', 'option');
INSERT INTO smsgatewayoption (id, gateway_id, "Key", "Value", "Type") VALUES (2, 1, 'PROJECT_ID',      'my-firebase-project',            'option');
INSERT INTO eventhandler (id, name, active, ordering, position, event, handlermodule, action) VALUES (1, 'send-email-on-fail', 1, 0, 'post', 'validate_check', 'privacyidea.lib.eventhandler.EmailEventHandler', 'sendmail');
INSERT INTO eventhandleroption (id, eventhandler_id, "Key", "Value") VALUES (1, 1, 'body',    'Authentication failed for {user}');
INSERT INTO eventhandleroption (id, eventhandler_id, "Key", "Value") VALUES (2, 1, 'subject', 'privacyIDEA authentication failure');
INSERT INTO eventhandlercondition (id, eventhandler_id, "Key", "Value", comparator) VALUES (1, 1, 'result_value', 'False', 'equal');
INSERT INTO smtpserver (id, identifier, server, port, sender, tls, enqueue_job) VALUES (1, 'default-smtp', 'mail.example.com', 587, 'noreply@example.com', 1, 0);
INSERT INTO clientapplication (id, ip, hostname, clienttype, node) VALUES (1, '10.0.0.1', 'vpnclient.example.com', 'PAM',    'pinode1');
INSERT INTO clientapplication (id, ip, hostname, clienttype, node) VALUES (2, '10.0.0.2', 'webserver.example.com', 'OAUTH2', 'pinode1');
INSERT INTO customuserattribute (id, user_id, resolver, realm_id, "Key", "Value") VALUES (1, '1000', 'defresolver', 1, 'department', 'engineering');
INSERT INTO serviceid (id, name, "Description") VALUES (1, 'ssh-servers', 'SSH key consumers');
INSERT INTO eventcounter (id, counter_name, counter_value, node) VALUES (1, 'failed_auth', 42, 'pinode1');
INSERT INTO eventcounter (id, counter_name, counter_value, node) VALUES (2, 'failed_auth', 17, 'pinode2');
INSERT INTO periodictask (id, name, active, retry_if_failed, interval, nodes, taskmodule, ordering, last_update) VALUES (1, 'cleanup-audit', 1, 1, '0 2 * * *', 'pinode1', 'privacyidea.lib.periodictask.AuditCleanup', 0, TIMESTAMP '2023-01-01 02:00:00');
INSERT INTO periodictaskoption (id, periodictask_id, key, value) VALUES (1, 1, 'age', '180d');
INSERT INTO periodictasklastrun (id, periodictask_id, node, timestamp) VALUES (1, 1, 'pinode1', TIMESTAMP '2023-06-01 02:00:00');
INSERT INTO monitoringstats (id, timestamp, stats_key, stats_value) VALUES (1, TIMESTAMP '2023-06-01 00:00:00', 'token_count',  47);
INSERT INTO monitoringstats (id, timestamp, stats_key, stats_value) VALUES (2, TIMESTAMP '2023-06-01 00:00:00', 'active_users', 39);
INSERT INTO pidea_audit (id, "date", action, success, serial, token_type, "user", realm, administrator, client, loglevel, clearance_level, thread_id) VALUES (1, TIMESTAMP '2023-06-01 10:00:00', 'validate/check', 1, 'HOTP0001', 'hotp', 'alice', 'defrealm', '', '10.0.0.1', 'INFO', 'default', '12345');
INSERT INTO pidea_audit (id, "date", action, success, serial, token_type, "user", realm, administrator, client, loglevel, clearance_level, thread_id) VALUES (2, TIMESTAMP '2023-06-01 10:01:00', 'validate/check', 0, 'TOTP0001', 'totp', 'alice', 'defrealm', '', '10.0.0.1', 'INFO', 'default', '12346');

-- ---------------------------------------------------------------------------
-- alembic_version -- stamp the DB at START_REVISION
-- ---------------------------------------------------------------------------
CREATE TABLE alembic_version (
    version_num VARCHAR2(32 CHAR) NOT NULL,
    PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num) VALUES ('5cb310101a1f');
