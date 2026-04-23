-- Auto-generated MariaDB seed SQL
-- Source: SQLAlchemy metadata
--
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE `admin` (
	username VARCHAR(120) NOT NULL, 
	password VARCHAR(255), 
	email VARCHAR(255), 
	PRIMARY KEY (username)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE authcache (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	first_auth DATETIME(6), 
	last_auth DATETIME(6), 
	username VARCHAR(64), 
	resolver VARCHAR(120), 
	realm VARCHAR(120), 
	client_ip VARCHAR(40), 
	user_agent VARCHAR(120), 
	auth_count INTEGER, 
	authentication VARCHAR(255), 
	PRIMARY KEY (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE caconnector (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(255) NOT NULL, 
	catype VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE challenge (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	transaction_id VARCHAR(64) NOT NULL, 
	data VARCHAR(512), 
	challenge VARCHAR(512), 
	`session` VARCHAR(512), 
	serial VARCHAR(40), 
	timestamp DATETIME(6), 
	expiration DATETIME(6), 
	received_count INTEGER, 
	otp_valid BOOL, 
	PRIMARY KEY (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE clientapplication (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	ip VARCHAR(255) NOT NULL, 
	hostname VARCHAR(255), 
	clienttype VARCHAR(255) NOT NULL, 
	lastseen DATETIME(6), 
	node VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT caix UNIQUE (ip, clienttype, node)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE config (
	`Key` VARCHAR(255) NOT NULL, 
	`Value` VARCHAR(2000), 
	`Type` VARCHAR(2000), 
	`Description` VARCHAR(2000), 
	PRIMARY KEY (`Key`)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE eventcounter (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	counter_name VARCHAR(80) NOT NULL, 
	counter_value INTEGER, 
	node VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT evctr_1 UNIQUE (counter_name, node)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE eventhandler (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(64), 
	active BOOL, 
	ordering INTEGER NOT NULL, 
	position VARCHAR(10), 
	event VARCHAR(255) NOT NULL, 
	handlermodule VARCHAR(255) NOT NULL, 
	`condition` VARCHAR(1024), 
	action VARCHAR(1024), 
	PRIMARY KEY (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE machineresolver (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(255) NOT NULL, 
	rtype VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE monitoringstats (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	timestamp DATETIME(6) NOT NULL, 
	stats_key VARCHAR(128) NOT NULL, 
	stats_value INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT msix_1 UNIQUE (timestamp, stats_key)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE passwordreset (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	recoverycode VARCHAR(255) NOT NULL, 
	username VARCHAR(64) NOT NULL, 
	realm VARCHAR(64) NOT NULL, 
	resolver VARCHAR(64), 
	email VARCHAR(255), 
	timestamp DATETIME(6), 
	expiration DATETIME(6), 
	PRIMARY KEY (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE periodictask (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(64) NOT NULL, 
	active BOOL NOT NULL, 
	retry_if_failed BOOL NOT NULL, 
	`interval` VARCHAR(256) NOT NULL, 
	nodes VARCHAR(256) NOT NULL, 
	taskmodule VARCHAR(256) NOT NULL, 
	ordering INTEGER NOT NULL, 
	last_update DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE pidea_audit (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	date DATETIME(6), 
	startdate DATETIME(6), 
	duration DATETIME(6), 
	signature VARCHAR(620), 
	action VARCHAR(50), 
	success INTEGER, 
	serial VARCHAR(40), 
	token_type VARCHAR(12), 
	user VARCHAR(20), 
	realm VARCHAR(20), 
	resolver VARCHAR(50), 
	administrator VARCHAR(20), 
	action_detail VARCHAR(50), 
	info VARCHAR(50), 
	privacyidea_server VARCHAR(255), 
	client VARCHAR(50), 
	loglevel VARCHAR(12), 
	clearance_level VARCHAR(12), 
	thread_id VARCHAR(20), 
	policies VARCHAR(255), 
	PRIMARY KEY (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE policy (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	active BOOL, 
	check_all_resolvers BOOL, 
	name VARCHAR(64) NOT NULL, 
	scope VARCHAR(32) NOT NULL, 
	action VARCHAR(2000), 
	realm VARCHAR(256), 
	adminrealm VARCHAR(256), 
	adminuser VARCHAR(256), 
	resolver VARCHAR(256), 
	pinode VARCHAR(256), 
	user VARCHAR(256), 
	client VARCHAR(256), 
	time VARCHAR(64), 
	priority INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE privacyideaserver (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	identifier VARCHAR(255) NOT NULL, 
	url VARCHAR(255) NOT NULL, 
	tls BOOL, 
	description VARCHAR(2000), 
	PRIMARY KEY (id), 
	UNIQUE (identifier)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE radiusserver (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	identifier VARCHAR(255) NOT NULL, 
	server VARCHAR(255) NOT NULL, 
	port INTEGER, 
	secret VARCHAR(255), 
	dictionary VARCHAR(255), 
	description VARCHAR(2000), 
	timeout INTEGER, 
	retries INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (identifier)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE realm (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(255) NOT NULL, 
	`default` BOOL, 
	`option` VARCHAR(40), 
	PRIMARY KEY (id), 
	UNIQUE (name)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE resolver (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(255) NOT NULL, 
	rtype VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE serviceid (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(255) NOT NULL, 
	`Description` VARCHAR(2000), 
	PRIMARY KEY (id), 
	UNIQUE (name)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE smsgateway (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	identifier VARCHAR(255) NOT NULL, 
	description VARCHAR(1024), 
	providermodule VARCHAR(1024) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (identifier)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE smtpserver (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	identifier VARCHAR(255) NOT NULL, 
	server VARCHAR(255) NOT NULL, 
	port INTEGER, 
	username VARCHAR(255), 
	password VARCHAR(255), 
	sender VARCHAR(255), 
	tls BOOL, 
	description VARCHAR(2000), 
	timeout INTEGER, 
	enqueue_job BOOL NOT NULL, 
	PRIMARY KEY (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE subscription (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	application VARCHAR(80), 
	for_name VARCHAR(80) NOT NULL, 
	for_address VARCHAR(128), 
	for_email VARCHAR(128) NOT NULL, 
	for_phone VARCHAR(50) NOT NULL, 
	for_url VARCHAR(80), 
	for_comment VARCHAR(255), 
	by_name VARCHAR(50) NOT NULL, 
	by_email VARCHAR(128) NOT NULL, 
	by_address VARCHAR(128), 
	by_phone VARCHAR(50), 
	by_url VARCHAR(80), 
	date_from DATETIME(6), 
	date_till DATETIME(6), 
	num_users INTEGER, 
	num_tokens INTEGER, 
	num_clients INTEGER, 
	level VARCHAR(80), 
	signature VARCHAR(640), 
	PRIMARY KEY (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE token (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	description VARCHAR(80), 
	serial VARCHAR(40) NOT NULL, 
	tokentype VARCHAR(30), 
	user_pin VARCHAR(512), 
	user_pin_iv VARCHAR(32), 
	so_pin VARCHAR(512), 
	so_pin_iv VARCHAR(32), 
	pin_seed VARCHAR(32), 
	otplen INTEGER, 
	pin_hash VARCHAR(512), 
	key_enc VARCHAR(2800), 
	key_iv VARCHAR(32), 
	maxfail INTEGER, 
	active BOOL NOT NULL, 
	revoked BOOL, 
	locked BOOL, 
	failcount INTEGER, 
	count INTEGER, 
	count_window INTEGER, 
	sync_window INTEGER, 
	rollout_state VARCHAR(10), 
	PRIMARY KEY (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE tokengroup (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(255) NOT NULL, 
	`Description` VARCHAR(2000), 
	PRIMARY KEY (id), 
	UNIQUE (name)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE usercache (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	username VARCHAR(64), 
	used_login VARCHAR(64), 
	resolver VARCHAR(120), 
	user_id VARCHAR(320), 
	timestamp DATETIME(6), 
	PRIMARY KEY (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE caconnectorconfig (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	caconnector_id INTEGER, 
	`Key` VARCHAR(255) NOT NULL, 
	`Value` VARCHAR(2000), 
	`Type` VARCHAR(2000), 
	`Description` VARCHAR(2000), 
	PRIMARY KEY (id), 
	CONSTRAINT ccix_2 UNIQUE (caconnector_id, `Key`), 
	FOREIGN KEY(caconnector_id) REFERENCES caconnector (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE customuserattribute (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(320), 
	resolver VARCHAR(120), 
	realm_id INTEGER, 
	`Key` VARCHAR(255) NOT NULL, 
	`Value` TEXT, 
	`Type` VARCHAR(100), 
	PRIMARY KEY (id), 
	FOREIGN KEY(realm_id) REFERENCES realm (id)
);

CREATE TABLE eventhandlercondition (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	eventhandler_id INTEGER, 
	`Key` VARCHAR(255) NOT NULL, 
	`Value` VARCHAR(2000), 
	comparator VARCHAR(255), 
	PRIMARY KEY (id), 
	CONSTRAINT ehcix_1 UNIQUE (eventhandler_id, `Key`), 
	FOREIGN KEY(eventhandler_id) REFERENCES eventhandler (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE eventhandleroption (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	eventhandler_id INTEGER, 
	`Key` VARCHAR(255) NOT NULL, 
	`Value` VARCHAR(2000), 
	`Type` VARCHAR(2000), 
	`Description` VARCHAR(2000), 
	PRIMARY KEY (id), 
	CONSTRAINT ehoix_1 UNIQUE (eventhandler_id, `Key`), 
	FOREIGN KEY(eventhandler_id) REFERENCES eventhandler (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE machineresolverconfig (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	resolver_id INTEGER, 
	`Key` VARCHAR(255) NOT NULL, 
	`Value` VARCHAR(2000), 
	`Type` VARCHAR(2000), 
	`Description` VARCHAR(2000), 
	PRIMARY KEY (id), 
	CONSTRAINT mrcix_2 UNIQUE (resolver_id, `Key`), 
	FOREIGN KEY(resolver_id) REFERENCES machineresolver (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE machinetoken (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	token_id INTEGER, 
	machineresolver_id INTEGER, 
	machine_id VARCHAR(255), 
	application VARCHAR(64), 
	PRIMARY KEY (id), 
	FOREIGN KEY(token_id) REFERENCES token (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE periodictasklastrun (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	periodictask_id INTEGER, 
	node VARCHAR(255) NOT NULL, 
	timestamp DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ptlrix_1 UNIQUE (periodictask_id, node), 
	FOREIGN KEY(periodictask_id) REFERENCES periodictask (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE periodictaskoption (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	periodictask_id INTEGER, 
	`key` VARCHAR(255) NOT NULL, 
	value VARCHAR(2000), 
	PRIMARY KEY (id), 
	CONSTRAINT ptoix_1 UNIQUE (periodictask_id, `key`), 
	FOREIGN KEY(periodictask_id) REFERENCES periodictask (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE policycondition (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	policy_id INTEGER NOT NULL, 
	section VARCHAR(255) NOT NULL, 
	`Key` VARCHAR(255) NOT NULL, 
	comparator VARCHAR(255) NOT NULL, 
	`Value` VARCHAR(2000) NOT NULL, 
	active BOOL NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(policy_id) REFERENCES policy (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE resolverconfig (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	resolver_id INTEGER, 
	`Key` VARCHAR(255) NOT NULL, 
	`Value` VARCHAR(2000), 
	`Type` VARCHAR(2000), 
	`Description` VARCHAR(2000), 
	PRIMARY KEY (id), 
	CONSTRAINT rcix_2 UNIQUE (resolver_id, `Key`), 
	FOREIGN KEY(resolver_id) REFERENCES resolver (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE resolverrealm (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	resolver_id INTEGER, 
	realm_id INTEGER, 
	priority INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT rrix_2 UNIQUE (resolver_id, realm_id), 
	FOREIGN KEY(resolver_id) REFERENCES resolver (id), 
	FOREIGN KEY(realm_id) REFERENCES realm (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE smsgatewayoption (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	`Key` VARCHAR(255) NOT NULL, 
	`Value` TEXT, 
	`Type` VARCHAR(100), 
	gateway_id INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT sgix_1 UNIQUE (gateway_id, `Key`, `Type`), 
	FOREIGN KEY(gateway_id) REFERENCES smsgateway (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE tokeninfo (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	`Key` VARCHAR(255) NOT NULL, 
	`Value` TEXT, 
	`Type` VARCHAR(100), 
	`Description` VARCHAR(2000), 
	token_id INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT tiix_2 UNIQUE (token_id, `Key`), 
	FOREIGN KEY(token_id) REFERENCES token (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE tokenowner (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	token_id INTEGER, 
	resolver VARCHAR(120), 
	user_id VARCHAR(320), 
	realm_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(token_id) REFERENCES token (id), 
	FOREIGN KEY(realm_id) REFERENCES realm (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE tokenrealm (
	id INTEGER AUTO_INCREMENT, 
	token_id INTEGER, 
	realm_id INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT trix_2 UNIQUE (token_id, realm_id), 
	FOREIGN KEY(token_id) REFERENCES token (id), 
	FOREIGN KEY(realm_id) REFERENCES realm (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE tokentokengroup (
	id INTEGER AUTO_INCREMENT, 
	token_id INTEGER, 
	tokengroup_id INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT ttgix_2 UNIQUE (token_id, tokengroup_id), 
	FOREIGN KEY(token_id) REFERENCES token (id), 
	FOREIGN KEY(tokengroup_id) REFERENCES tokengroup (id)
)ROW_FORMAT=DYNAMIC;

CREATE TABLE machinetokenoptions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	machinetoken_id INTEGER, 
	mt_key VARCHAR(64) NOT NULL, 
	mt_value VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(machinetoken_id) REFERENCES machinetoken (id)
)ROW_FORMAT=DYNAMIC;


-- ---------------------------------------------------------------------------
-- Data
-- ---------------------------------------------------------------------------

INSERT INTO `config` (`Key`, `Value`, `Type`, `Description`) VALUES
    ('PI_PEPPER',          'dGVzdHBlcHBlcg==', 'password', 'Pepper for hashing'),
    ('DefaultOtpLen',      '6',                '',         ''),
    ('DefaultMaxFailCount','10',               '',         ''),
    ('__timestamp__',      '1680000000',       '',         'config timestamp. last changed.');

-- ---------------------------------------------------------------------------
-- realm
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `realm` (
    `id`      INT          NOT NULL AUTO_INCREMENT,
    `name`    VARCHAR(255) NOT NULL UNIQUE,
    `default` TINYINT(1)   DEFAULT 0,
    `option`  VARCHAR(40)  DEFAULT '',
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `realm` (`id`, `name`, `default`) VALUES
    (1, 'defrealm', 1),
    (2, 'testrealm', 0);

-- ---------------------------------------------------------------------------
-- resolver
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `resolver` (
    `id`    INT          NOT NULL AUTO_INCREMENT,
    `name`  VARCHAR(255) NOT NULL UNIQUE,
    `rtype` VARCHAR(255) NOT NULL DEFAULT '',
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `resolver` (`id`, `name`, `rtype`) VALUES
    (1, 'defresolver', 'passwdresolver');

-- ---------------------------------------------------------------------------
-- resolverconfig
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `resolverconfig` (
    `id`          INT          NOT NULL AUTO_INCREMENT,
    `resolver_id` INT,
    `Key`         VARCHAR(255) NOT NULL,
    `Value`       VARCHAR(2000) DEFAULT '',
    `Type`        VARCHAR(2000) DEFAULT '',
    `Description` VARCHAR(2000) DEFAULT '',
    PRIMARY KEY (`id`),
    UNIQUE KEY `rcix_2` (`resolver_id`, `Key`),
    FOREIGN KEY (`resolver_id`) REFERENCES `resolver`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `resolverconfig` (`resolver_id`, `Key`, `Value`) VALUES
    (1, 'fileName', '/etc/passwd');

-- ---------------------------------------------------------------------------
-- resolverrealm
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `resolverrealm` (
    `id`          INT NOT NULL AUTO_INCREMENT,
    `resolver_id` INT,
    `realm_id`    INT,
    `priority`    INT,
    PRIMARY KEY (`id`),
    UNIQUE KEY `rrix_2` (`resolver_id`, `realm_id`),
    FOREIGN KEY (`resolver_id`) REFERENCES `resolver`(`id`),
    FOREIGN KEY (`realm_id`)   REFERENCES `realm`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `resolverrealm` (`resolver_id`, `realm_id`, `priority`) VALUES
    (1, 1, 1),
    (1, 2, 1);

-- ---------------------------------------------------------------------------
-- token
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `token` (
    `id`           INT           NOT NULL AUTO_INCREMENT,
    `description`  VARCHAR(80)   DEFAULT '',
    `serial`       VARCHAR(40)   NOT NULL UNIQUE,
    `tokentype`    VARCHAR(30)   DEFAULT 'HOTP',
    `user_pin`     VARCHAR(512)  DEFAULT '',
    `user_pin_iv`  VARCHAR(32)   DEFAULT '',
    `so_pin`       VARCHAR(512)  DEFAULT '',
    `so_pin_iv`    VARCHAR(32)   DEFAULT '',
    `pin_seed`     VARCHAR(32)   DEFAULT '',
    `otplen`       INT           DEFAULT 6,
    `pin_hash`     VARCHAR(512)  DEFAULT '',
    `key_enc`      VARCHAR(2800) DEFAULT '',
    `key_iv`       VARCHAR(32)   DEFAULT '',
    `maxfail`      INT           DEFAULT 10,
    `active`       TINYINT(1)    NOT NULL DEFAULT 1,
    `revoked`      TINYINT(1)    DEFAULT 0,
    `locked`       TINYINT(1)    DEFAULT 0,
    `failcount`    INT           DEFAULT 0,
    `count`        INT           DEFAULT 0,
    `count_window` INT           DEFAULT 10,
    `sync_window`  INT           DEFAULT 1000,
    `rollout_state` VARCHAR(10)  DEFAULT '',
    PRIMARY KEY (`id`),
    INDEX `ix_token_serial`    (`serial`),
    INDEX `ix_token_tokentype` (`tokentype`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `token` (`id`, `serial`, `tokentype`, `otplen`, `active`, `key_enc`, `key_iv`, `pin_hash`) VALUES
    (1, 'HOTP0001', 'hotp', 6, 1, 'aabbccddeeff00112233445566778899aabbccddeeff001122334455', '00112233445566778899aabbccdd0011', '$pbkdf2-sha512$...fakehash...'),
    (2, 'TOTP0001', 'totp', 6, 1, 'aabbccddeeff00112233445566778899aabbccddeeff001122334455', '00112233445566778899aabbccdd0022', ''),
    (3, 'PIPU0001', 'push', 6, 1, '', '', '');

-- ---------------------------------------------------------------------------
-- tokeninfo
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `tokeninfo` (
    `id`          INT           NOT NULL AUTO_INCREMENT,
    `Key`         VARCHAR(255)  NOT NULL,
    `Value`       LONGTEXT      DEFAULT '',
    `Type`        VARCHAR(100)  DEFAULT '',
    `Description` VARCHAR(2000) DEFAULT '',
    `token_id`    INT,
    PRIMARY KEY (`id`),
    UNIQUE KEY `tiix_2` (`token_id`, `Key`),
    INDEX `ix_tokeninfo_token_id` (`token_id`),
    FOREIGN KEY (`token_id`) REFERENCES `token`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `tokeninfo` (`token_id`, `Key`, `Value`) VALUES
    (2, 'timeStep',   '30'),
    (2, 'timeWindow', '180'),
    (3, 'firebase_config', 'myFirebase'),
    (3, 'public_key_smartphone', 'fakePublicKey==');

-- ---------------------------------------------------------------------------
-- tokenowner
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `tokenowner` (
    `id`       INT          NOT NULL AUTO_INCREMENT,
    `token_id` INT,
    `resolver` VARCHAR(120) DEFAULT '',
    `user_id`  VARCHAR(320) DEFAULT '',
    `realm_id` INT,
    PRIMARY KEY (`id`),
    INDEX `ix_tokenowner_resolver` (`resolver`),
    INDEX `ix_tokenowner_user_id`  (`user_id`),
    FOREIGN KEY (`token_id`) REFERENCES `token`(`id`),
    FOREIGN KEY (`realm_id`) REFERENCES `realm`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `tokenowner` (`token_id`, `resolver`, `user_id`, `realm_id`) VALUES
    (1, 'defresolver', '1000', 1),
    (2, 'defresolver', '1000', 1);

-- ---------------------------------------------------------------------------
-- tokenrealm
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `tokenrealm` (
    `id`       INT NOT NULL AUTO_INCREMENT,
    `token_id` INT,
    `realm_id` INT,
    PRIMARY KEY (`id`),
    UNIQUE KEY `trix_2` (`token_id`, `realm_id`),
    FOREIGN KEY (`token_id`) REFERENCES `token`(`id`),
    FOREIGN KEY (`realm_id`) REFERENCES `realm`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `tokenrealm` (`token_id`, `realm_id`) VALUES
    (1, 1),
    (2, 1),
    (3, 1);

-- ---------------------------------------------------------------------------
-- tokengroup
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `tokengroup` (
    `id`          INT          NOT NULL AUTO_INCREMENT,
    `name`        VARCHAR(255) NOT NULL UNIQUE,
    `Description` VARCHAR(2000) DEFAULT '',
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `tokengroup` (`id`, `name`, `Description`) VALUES
    (1, 'vpn-tokens',   'Tokens used for VPN access'),
    (2, 'admin-tokens',  'Tokens for administrators');

-- ---------------------------------------------------------------------------
-- tokentokengroup
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `tokentokengroup` (
    `id`           INT NOT NULL AUTO_INCREMENT,
    `token_id`     INT,
    `tokengroup_id` INT,
    PRIMARY KEY (`id`),
    UNIQUE KEY `ttgix_2` (`token_id`, `tokengroup_id`),
    FOREIGN KEY (`token_id`)      REFERENCES `token`(`id`),
    FOREIGN KEY (`tokengroup_id`) REFERENCES `tokengroup`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `tokentokengroup` (`token_id`, `tokengroup_id`) VALUES
    (1, 1),
    (2, 2);

-- ---------------------------------------------------------------------------
-- caconnector
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `caconnector` (
    `id`     INT          NOT NULL AUTO_INCREMENT,
    `name`   VARCHAR(255) NOT NULL UNIQUE,
    `catype` VARCHAR(255) NOT NULL DEFAULT '',
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- caconnectorconfig
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `caconnectorconfig` (
    `id`              INT           NOT NULL AUTO_INCREMENT,
    `caconnector_id`  INT,
    `Key`             VARCHAR(255)  NOT NULL,
    `Value`           VARCHAR(2000) DEFAULT '',
    `Type`            VARCHAR(2000) DEFAULT '',
    `Description`     VARCHAR(2000) DEFAULT '',
    PRIMARY KEY (`id`),
    UNIQUE KEY `ccix_2` (`caconnector_id`, `Key`),
    FOREIGN KEY (`caconnector_id`) REFERENCES `caconnector`(`id`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- policy
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `policy` (
    `id`                   INT           NOT NULL AUTO_INCREMENT,
    `active`               TINYINT(1)    DEFAULT 1,
    `check_all_resolvers`  TINYINT(1)    DEFAULT 0,
    `name`                 VARCHAR(64)   NOT NULL UNIQUE,
    `scope`                VARCHAR(32)   NOT NULL,
    `action`               VARCHAR(2000) DEFAULT '',
    `realm`                VARCHAR(256)  DEFAULT '',
    `adminrealm`           VARCHAR(256)  DEFAULT '',
    `adminuser`            VARCHAR(256)  DEFAULT '',
    `resolver`             VARCHAR(256)  DEFAULT '',
    `pinode`               VARCHAR(256)  DEFAULT '',
    `user`                 VARCHAR(256)  DEFAULT '',
    `client`               VARCHAR(256)  DEFAULT '',
    `time`                 VARCHAR(64)   DEFAULT '',
    `priority`             INT           NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `policy` (`id`, `active`, `name`, `scope`, `action`, `realm`, `priority`) VALUES
    (1, 1, 'superuser',         'admin', 'superuser',                     '',        1),
    (2, 1, 'enroll-hotp',       'enroll','enrollHOTP',                    'defrealm',1),
    (3, 1, 'no-detail-on-fail', 'authz', 'no_detail_on_fail',             '',        1),
    (4, 0, 'disabled-policy',   'auth',  'push_wait=20',                  '',        1);

-- ---------------------------------------------------------------------------
-- policycondition
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `policycondition` (
    `id`         INT           NOT NULL AUTO_INCREMENT,
    `policy_id`  INT           NOT NULL,
    `section`    VARCHAR(255)  NOT NULL,
    `Key`        VARCHAR(255)  NOT NULL,
    `comparator` VARCHAR(255)  NOT NULL DEFAULT 'equals',
    `Value`      VARCHAR(2000) NOT NULL DEFAULT '',
    `active`     TINYINT(1)    NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    FOREIGN KEY (`policy_id`) REFERENCES `policy`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `policycondition` (`policy_id`, `section`, `Key`, `comparator`, `Value`, `active`) VALUES
    (2, 'userinfo', 'memberOf', 'equals', 'cn=vpn,dc=example,dc=com', 1);

-- ---------------------------------------------------------------------------
-- challenge
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `challenge` (
    `id`             INT          NOT NULL AUTO_INCREMENT,
    `transaction_id` VARCHAR(64)  NOT NULL,
    `data`           VARCHAR(512) DEFAULT '',
    `challenge`      VARCHAR(512) DEFAULT '',
    `session`        VARCHAR(512) DEFAULT '',
    `serial`         VARCHAR(40)  DEFAULT '',
    `timestamp`      DATETIME(6)  DEFAULT NULL,
    `expiration`     DATETIME(6),
    `received_count` INT          DEFAULT 0,
    `otp_valid`      TINYINT(1)   DEFAULT 0,
    PRIMARY KEY (`id`),
    INDEX `ix_challenge_transaction_id` (`transaction_id`),
    INDEX `ix_challenge_serial`         (`serial`),
    INDEX `ix_challenge_timestamp`      (`timestamp`)
) ROW_FORMAT=DYNAMIC;

-- No challenge rows: challenges are ephemeral and not meaningful to preserve across migrations.

-- ---------------------------------------------------------------------------
-- admin
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `admin` (
    `username` VARCHAR(120) NOT NULL,
    `password` VARCHAR(255),
    `email`    VARCHAR(255),
    PRIMARY KEY (`username`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `admin` (`username`, `password`, `email`) VALUES
    ('admin', '$pbkdf2-sha512$25000$fakesalt$fakehash==', 'admin@example.com');

-- ---------------------------------------------------------------------------
-- machineresolver
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `machineresolver` (
    `id`    INT          NOT NULL AUTO_INCREMENT,
    `name`  VARCHAR(255) NOT NULL UNIQUE,
    `rtype` VARCHAR(255) NOT NULL DEFAULT '',
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- machineresolverconfig
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `machineresolverconfig` (
    `id`          INT           NOT NULL AUTO_INCREMENT,
    `resolver_id` INT,
    `Key`         VARCHAR(255)  NOT NULL,
    `Value`       VARCHAR(2000) DEFAULT '',
    `Type`        VARCHAR(2000) DEFAULT '',
    `Description` VARCHAR(2000) DEFAULT '',
    PRIMARY KEY (`id`),
    UNIQUE KEY `mrcix_2` (`resolver_id`, `Key`),
    FOREIGN KEY (`resolver_id`) REFERENCES `machineresolver`(`id`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- machinetoken
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `machinetoken` (
    `id`                  INT          NOT NULL AUTO_INCREMENT,
    `token_id`            INT,
    `machineresolver_id`  INT,
    `machine_id`          VARCHAR(255),
    `application`         VARCHAR(64),
    PRIMARY KEY (`id`),
    FOREIGN KEY (`token_id`) REFERENCES `token`(`id`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- machinetokenoptions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `machinetokenoptions` (
    `id`               INT         NOT NULL AUTO_INCREMENT,
    `machinetoken_id`  INT,
    `mt_key`           VARCHAR(64) NOT NULL,
    `mt_value`         VARCHAR(64) NOT NULL,
    PRIMARY KEY (`id`),
    FOREIGN KEY (`machinetoken_id`) REFERENCES `machinetoken`(`id`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- smsgateway
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `smsgateway` (
    `id`             INT           NOT NULL AUTO_INCREMENT,
    `identifier`     VARCHAR(255)  NOT NULL UNIQUE,
    `description`    VARCHAR(1024) DEFAULT '',
    `providermodule` VARCHAR(1024) NOT NULL,
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `smsgateway` (`id`, `identifier`, `description`, `providermodule`) VALUES
    (1, 'myFirebase', 'Firebase push gateway', 'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider');

-- ---------------------------------------------------------------------------
-- smsgatewayoption
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `smsgatewayoption` (
    `id`         INT          NOT NULL AUTO_INCREMENT,
    `Key`        VARCHAR(255) NOT NULL,
    `Value`      LONGTEXT     DEFAULT '',
    `Type`       VARCHAR(100) DEFAULT 'option',
    `gateway_id` INT,
    PRIMARY KEY (`id`),
    UNIQUE KEY `sgix_1` (`gateway_id`, `Key`, `Type`),
    INDEX `ix_smsgatewayoption_gateway_id` (`gateway_id`),
    FOREIGN KEY (`gateway_id`) REFERENCES `smsgateway`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `smsgatewayoption` (`gateway_id`, `Key`, `Value`, `Type`) VALUES
    (1, 'FIREBASE_CONFIG', '/etc/privacyidea/firebase.json', 'option'),
    (1, 'PROJECT_ID',      'my-firebase-project',            'option');

-- ---------------------------------------------------------------------------
-- eventhandler
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `eventhandler` (
    `id`           INT           NOT NULL AUTO_INCREMENT,
    `name`         VARCHAR(64),
    `active`       TINYINT(1)    DEFAULT 1,
    `ordering`     INT           NOT NULL DEFAULT 0,
    `position`     VARCHAR(10)   DEFAULT 'post',
    `event`        VARCHAR(255)  NOT NULL,
    `handlermodule` VARCHAR(255) NOT NULL,
    `condition`    VARCHAR(1024) DEFAULT '',
    `action`       VARCHAR(1024) DEFAULT '',
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `eventhandler` (`id`, `name`, `active`, `ordering`, `position`, `event`, `handlermodule`, `action`) VALUES
    (1, 'send-email-on-fail', 1, 0, 'post', 'validate_check', 'privacyidea.lib.eventhandler.EmailEventHandler', 'sendmail');

-- ---------------------------------------------------------------------------
-- eventhandleroption
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `eventhandleroption` (
    `id`               INT           NOT NULL AUTO_INCREMENT,
    `eventhandler_id`  INT,
    `Key`              VARCHAR(255)  NOT NULL,
    `Value`            VARCHAR(2000) DEFAULT '',
    `Type`             VARCHAR(2000) DEFAULT '',
    `Description`      VARCHAR(2000) DEFAULT '',
    PRIMARY KEY (`id`),
    UNIQUE KEY `ehoix_1` (`eventhandler_id`, `Key`),
    FOREIGN KEY (`eventhandler_id`) REFERENCES `eventhandler`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `eventhandleroption` (`eventhandler_id`, `Key`, `Value`) VALUES
    (1, 'body',    'Authentication failed for {user}'),
    (1, 'subject', 'privacyIDEA authentication failure');

-- ---------------------------------------------------------------------------
-- eventhandlercondition
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `eventhandlercondition` (
    `id`               INT           NOT NULL AUTO_INCREMENT,
    `eventhandler_id`  INT,
    `Key`              VARCHAR(255)  NOT NULL,
    `Value`            VARCHAR(2000) DEFAULT '',
    `comparator`       VARCHAR(255)  DEFAULT 'equal',
    PRIMARY KEY (`id`),
    UNIQUE KEY `ehcix_1` (`eventhandler_id`, `Key`),
    FOREIGN KEY (`eventhandler_id`) REFERENCES `eventhandler`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `eventhandlercondition` (`eventhandler_id`, `Key`, `Value`, `comparator`) VALUES
    (1, 'result_value', 'False', 'equal');

-- ---------------------------------------------------------------------------
-- smtpserver
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `smtpserver` (
    `id`          INT          NOT NULL AUTO_INCREMENT,
    `identifier`  VARCHAR(255) NOT NULL,
    `server`      VARCHAR(255) NOT NULL,
    `port`        INT          DEFAULT 25,
    `username`    VARCHAR(255) DEFAULT '',
    `password`    VARCHAR(255) DEFAULT '',
    `sender`      VARCHAR(255) DEFAULT '',
    `tls`         TINYINT(1)   DEFAULT 0,
    `description` VARCHAR(2000) DEFAULT '',
    `timeout`     INT          DEFAULT 10,
    `enqueue_job` TINYINT(1)   NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `smtpserver` (`id`, `identifier`, `server`, `port`, `sender`, `tls`, `enqueue_job`) VALUES
    (1, 'default-smtp', 'mail.example.com', 587, 'noreply@example.com', 1, 0);

-- ---------------------------------------------------------------------------
-- radiusserver
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `radiusserver` (
    `id`          INT          NOT NULL AUTO_INCREMENT,
    `identifier`  VARCHAR(255) NOT NULL UNIQUE,
    `server`      VARCHAR(255) NOT NULL,
    `port`        INT          DEFAULT 25,
    `secret`      VARCHAR(255) DEFAULT '',
    `dictionary`  VARCHAR(255) DEFAULT '/etc/privacyidea/dictionary',
    `description` VARCHAR(2000) DEFAULT '',
    `timeout`     INT          DEFAULT 5,
    `retries`     INT          DEFAULT 3,
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- privacyideaserver
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `privacyideaserver` (
    `id`          INT          NOT NULL AUTO_INCREMENT,
    `identifier`  VARCHAR(255) NOT NULL UNIQUE,
    `url`         VARCHAR(255) NOT NULL,
    `tls`         TINYINT(1)   DEFAULT 0,
    `description` VARCHAR(2000) DEFAULT '',
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- clientapplication
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `clientapplication` (
    `id`         INT          NOT NULL AUTO_INCREMENT,
    `ip`         VARCHAR(255) NOT NULL,
    `hostname`   VARCHAR(255),
    `clienttype` VARCHAR(255) NOT NULL,
    `lastseen`   DATETIME(6)  DEFAULT NULL,
    `node`       VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `caix` (`ip`, `clienttype`, `node`),
    INDEX `ix_clientapplication_ip`         (`ip`),
    INDEX `ix_clientapplication_clienttype` (`clienttype`),
    INDEX `ix_clientapplication_lastseen`   (`lastseen`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `clientapplication` (`ip`, `hostname`, `clienttype`, `node`) VALUES
    ('10.0.0.1', 'vpnclient.example.com', 'PAM',    'pinode1'),
    ('10.0.0.2', 'webserver.example.com', 'OAUTH2', 'pinode1');

-- ---------------------------------------------------------------------------
-- subscription
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `subscription` (
    `id`          INT          NOT NULL AUTO_INCREMENT,
    `application` VARCHAR(80),
    `for_name`    VARCHAR(80)  NOT NULL,
    `for_address` VARCHAR(128),
    `for_email`   VARCHAR(128) NOT NULL,
    `for_phone`   VARCHAR(50)  NOT NULL,
    `for_url`     VARCHAR(80),
    `for_comment` VARCHAR(255),
    `by_name`     VARCHAR(50)  NOT NULL,
    `by_email`    VARCHAR(128) NOT NULL,
    `by_address`  VARCHAR(128),
    `by_phone`    VARCHAR(50),
    `by_url`      VARCHAR(80),
    `date_from`   DATETIME,
    `date_till`   DATETIME,
    `num_users`   INT,
    `num_tokens`  INT,
    `num_clients` INT,
    `level`       VARCHAR(80),
    `signature`   VARCHAR(640),
    PRIMARY KEY (`id`),
    INDEX `ix_subscription_application` (`application`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- customuserattribute
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `customuserattribute` (
    `id`       INT          NOT NULL AUTO_INCREMENT,
    `user_id`  VARCHAR(320) DEFAULT '',
    `resolver` VARCHAR(120) DEFAULT '',
    `realm_id` INT,
    `Key`      VARCHAR(255) NOT NULL,
    `Value`    LONGTEXT     DEFAULT '',
    `Type`     VARCHAR(100) DEFAULT '',
    PRIMARY KEY (`id`),
    INDEX `ix_customuserattribute_user_id`  (`user_id`),
    INDEX `ix_customuserattribute_resolver` (`resolver`),
    FOREIGN KEY (`realm_id`) REFERENCES `realm`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `customuserattribute` (`user_id`, `resolver`, `realm_id`, `Key`, `Value`) VALUES
    ('1000', 'defresolver', 1, 'department', 'engineering');

-- ---------------------------------------------------------------------------
-- serviceid
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `serviceid` (
    `id`          INT          NOT NULL AUTO_INCREMENT,
    `name`        VARCHAR(255) NOT NULL UNIQUE,
    `Description` VARCHAR(2000) DEFAULT '',
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `serviceid` (`id`, `name`, `Description`) VALUES
    (1, 'ssh-servers', 'SSH key consumers');

-- ---------------------------------------------------------------------------
-- passwordreset
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `passwordreset` (
    `id`           INT          NOT NULL AUTO_INCREMENT,
    `recoverycode` VARCHAR(255) NOT NULL,
    `username`     VARCHAR(64)  NOT NULL,
    `realm`        VARCHAR(64)  NOT NULL,
    `resolver`     VARCHAR(64),
    `email`        VARCHAR(255),
    `timestamp`    DATETIME,
    `expiration`   DATETIME,
    PRIMARY KEY (`id`),
    INDEX `ix_passwordreset_username` (`username`),
    INDEX `ix_passwordreset_realm`    (`realm`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- usercache
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `usercache` (
    `id`        INT          NOT NULL AUTO_INCREMENT,
    `username`  VARCHAR(64)  DEFAULT '',
    `used_login` VARCHAR(64) DEFAULT '',
    `resolver`  VARCHAR(120) DEFAULT '',
    `user_id`   VARCHAR(320) DEFAULT '',
    `timestamp` DATETIME,
    PRIMARY KEY (`id`),
    INDEX `ix_usercache_username`  (`username`),
    INDEX `ix_usercache_used_login` (`used_login`),
    INDEX `ix_usercache_user_id`   (`user_id`),
    INDEX `ix_usercache_timestamp` (`timestamp`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- authcache
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `authcache` (
    `id`             INT          NOT NULL AUTO_INCREMENT,
    `first_auth`     DATETIME,
    `last_auth`      DATETIME,
    `username`       VARCHAR(64)  DEFAULT '',
    `resolver`       VARCHAR(120) DEFAULT '',
    `realm`          VARCHAR(120) DEFAULT '',
    `client_ip`      VARCHAR(40)  DEFAULT '',
    `user_agent`     VARCHAR(120) DEFAULT '',
    `auth_count`     INT          DEFAULT 0,
    `authentication` VARCHAR(255) DEFAULT '',
    PRIMARY KEY (`id`),
    INDEX `ix_authcache_first_auth` (`first_auth`),
    INDEX `ix_authcache_last_auth`  (`last_auth`),
    INDEX `ix_authcache_username`   (`username`),
    INDEX `ix_authcache_resolver`   (`resolver`),
    INDEX `ix_authcache_realm`      (`realm`)
) ROW_FORMAT=DYNAMIC;

-- ---------------------------------------------------------------------------
-- eventcounter
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `eventcounter` (
    `id`            INT          NOT NULL AUTO_INCREMENT,
    `counter_name`  VARCHAR(80)  NOT NULL,
    `counter_value` INT          DEFAULT 0,
    `node`          VARCHAR(255) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `evctr_1` (`counter_name`, `node`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `eventcounter` (`counter_name`, `counter_value`, `node`) VALUES
    ('failed_auth', 42, 'pinode1'),
    ('failed_auth', 17, 'pinode2');

-- ---------------------------------------------------------------------------
-- periodictask
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `periodictask` (
    `id`              INT          NOT NULL AUTO_INCREMENT,
    `name`            VARCHAR(64)  NOT NULL UNIQUE,
    `active`          TINYINT(1)   NOT NULL DEFAULT 1,
    `retry_if_failed` TINYINT(1)   NOT NULL DEFAULT 1,
    `interval`        VARCHAR(256) NOT NULL,
    `nodes`           VARCHAR(256) NOT NULL,
    `taskmodule`      VARCHAR(256) NOT NULL,
    `ordering`        INT          NOT NULL DEFAULT 0,
    `last_update`     DATETIME     NOT NULL,
    PRIMARY KEY (`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `periodictask` (`id`, `name`, `active`, `retry_if_failed`, `interval`, `nodes`, `taskmodule`, `ordering`, `last_update`) VALUES
    (1, 'cleanup-audit', 1, 1, '0 2 * * *', 'pinode1', 'privacyidea.lib.periodictask.AuditCleanup', 0, '2023-01-01 02:00:00');

-- ---------------------------------------------------------------------------
-- periodictaskoption
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `periodictaskoption` (
    `id`               INT          NOT NULL AUTO_INCREMENT,
    `periodictask_id`  INT,
    `key`              VARCHAR(255) NOT NULL,
    `value`            VARCHAR(2000) DEFAULT '',
    PRIMARY KEY (`id`),
    UNIQUE KEY `ptoix_1` (`periodictask_id`, `key`),
    FOREIGN KEY (`periodictask_id`) REFERENCES `periodictask`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `periodictaskoption` (`periodictask_id`, `key`, `value`) VALUES
    (1, 'age', '180d');

-- ---------------------------------------------------------------------------
-- periodictasklastrun
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `periodictasklastrun` (
    `id`               INT          NOT NULL AUTO_INCREMENT,
    `periodictask_id`  INT,
    `node`             VARCHAR(255) NOT NULL,
    `timestamp`        DATETIME     NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `ptlrix_1` (`periodictask_id`, `node`),
    FOREIGN KEY (`periodictask_id`) REFERENCES `periodictask`(`id`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `periodictasklastrun` (`periodictask_id`, `node`, `timestamp`) VALUES
    (1, 'pinode1', '2023-06-01 02:00:00');

-- ---------------------------------------------------------------------------
-- monitoringstats
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `monitoringstats` (
    `id`          INT          NOT NULL AUTO_INCREMENT,
    `timestamp`   DATETIME     NOT NULL,
    `stats_key`   VARCHAR(128) NOT NULL,
    `stats_value` INT          NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    UNIQUE KEY `msix_1` (`timestamp`, `stats_key`),
    INDEX `ix_monitoringstats_timestamp` (`timestamp`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `monitoringstats` (`timestamp`, `stats_key`, `stats_value`) VALUES
    ('2023-06-01 00:00:00', 'token_count',  47),
    ('2023-06-01 00:00:00', 'active_users', 39);

-- ---------------------------------------------------------------------------
-- pidea_audit
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `pidea_audit` (
    `id`                INT          NOT NULL AUTO_INCREMENT,
    `date`              DATETIME(6),
    `startdate`         DATETIME(6),
    `duration`          TIME(6),
    `signature`         VARCHAR(620),
    `action`            VARCHAR(50),
    `success`           INT,
    `serial`            VARCHAR(40),
    `token_type`        VARCHAR(12),
    `user`              VARCHAR(20),
    `realm`             VARCHAR(20),
    `resolver`          VARCHAR(50),
    `administrator`     VARCHAR(20),
    `action_detail`     VARCHAR(50),
    `info`              VARCHAR(50),
    `privacyidea_server` VARCHAR(255),
    `client`            VARCHAR(50),
    `loglevel`          VARCHAR(12),
    `clearance_level`   VARCHAR(12),
    `thread_id`         VARCHAR(20),
    `policies`          VARCHAR(255),
    PRIMARY KEY (`id`),
    INDEX `ix_pidea_audit_date` (`date`),
    INDEX `ix_pidea_audit_user` (`user`)
) ROW_FORMAT=DYNAMIC;

INSERT INTO `pidea_audit` (`date`, `action`, `success`, `serial`, `token_type`, `user`, `realm`, `administrator`, `client`, `loglevel`, `clearance_level`, `thread_id`) VALUES
    ('2023-06-01 10:00:00', 'validate/check', 1, 'HOTP0001', 'hotp', 'alice', 'defrealm', '', '10.0.0.1', 'INFO', 'default', '12345'),
    ('2023-06-01 10:01:00', 'validate/check', 0, 'TOTP0001', 'totp', 'alice', 'defrealm', '', '10.0.0.1', 'INFO', 'default', '12346');

-- ---------------------------------------------------------------------------
-- Sequences (MariaDB 10.3+)
--
-- v3.9 migration 5cb310101a1f walks model metadata and creates one sequence
-- per integer-PK table whose model column declares Sequence(). Real installs
-- ran that body, but the seed is stamped at exactly that revision so its
-- body is skipped on upgrade. We therefore bake the resulting CREATE
-- SEQUENCEs in directly to match the on-disk state of an upgraded install.
-- START WITH values match MAX(id)+1 of the seeded data so the next nextval
-- returns a free PK.
-- ---------------------------------------------------------------------------
CREATE SEQUENCE `audit_seq` START WITH 3;
CREATE SEQUENCE `authcache_seq` START WITH 1;
CREATE SEQUENCE `caconfig_seq` START WITH 1;
CREATE SEQUENCE `caconnector_seq` START WITH 1;
CREATE SEQUENCE `challenge_seq` START WITH 1;
CREATE SEQUENCE `clientapp_seq` START WITH 3;
CREATE SEQUENCE `customuserattribute_seq` START WITH 2;
CREATE SEQUENCE `eventcounter_seq` START WITH 3;
CREATE SEQUENCE `eventhandler_seq` START WITH 2;
CREATE SEQUENCE `eventhandlercond_seq` START WITH 2;
CREATE SEQUENCE `eventhandleropt_seq` START WITH 3;
CREATE SEQUENCE `machineresolver_seq` START WITH 1;
CREATE SEQUENCE `machineresolverconf_seq` START WITH 1;
CREATE SEQUENCE `machinetoken_seq` START WITH 1;
CREATE SEQUENCE `machtokenopt_seq` START WITH 1;
CREATE SEQUENCE `monitoringstats_seq` START WITH 3;
CREATE SEQUENCE `periodictask_seq` START WITH 2;
CREATE SEQUENCE `periodictasklastrun_seq` START WITH 2;
CREATE SEQUENCE `periodictaskopt_seq` START WITH 2;
CREATE SEQUENCE `policy_seq` START WITH 5;
CREATE SEQUENCE `policycondition_seq` START WITH 2;
CREATE SEQUENCE `privacyideaserver_seq` START WITH 1;
CREATE SEQUENCE `pwreset_seq` START WITH 1;
CREATE SEQUENCE `radiusserver_seq` START WITH 1;
CREATE SEQUENCE `realm_seq` START WITH 3;
CREATE SEQUENCE `resolver_seq` START WITH 2;
CREATE SEQUENCE `resolverconf_seq` START WITH 2;
CREATE SEQUENCE `resolverrealm_seq` START WITH 3;
CREATE SEQUENCE `serviceid_seq` START WITH 2;
CREATE SEQUENCE `smsgateway_seq` START WITH 2;
CREATE SEQUENCE `smsgwoption_seq` START WITH 3;
CREATE SEQUENCE `smtpserver_seq` START WITH 2;
CREATE SEQUENCE `subscription_seq` START WITH 1;
CREATE SEQUENCE `token_seq` START WITH 4;
CREATE SEQUENCE `tokeninfo_seq` START WITH 5;
CREATE SEQUENCE `tokenowner_seq` START WITH 3;
CREATE SEQUENCE `tokenrealm_seq` START WITH 4;
CREATE SEQUENCE `usercache_seq` START WITH 1;

-- ---------------------------------------------------------------------------
-- alembic_version — stamp the DB at START_REVISION
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `alembic_version` (
    `version_num` VARCHAR(32) NOT NULL,
    PRIMARY KEY (`version_num`)
);

INSERT INTO `alembic_version` (`version_num`) VALUES ('5cb310101a1f');


SET FOREIGN_KEY_CHECKS = 1;
