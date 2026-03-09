-- Seed data for migration tests pinned at START_REVISION 5cb310101a1f (v3.9)
-- Dialect: PostgreSQL
--
-- This file represents a realistic privacyIDEA v3.9 database state.
-- It is written in native PostgreSQL syntax.
--
-- Usage:
--   engine = create_engine(DB_URL)
--   with engine.connect() as conn:
--       for stmt in _read_seed_sql(path):
--           conn.execute(text(stmt))
--       conn.commit()
--   command.stamp(cfg, "5cb310101a1f")

-- ---------------------------------------------------------------------------
-- Sequences (used by SQLAlchemy ORM instead of SERIAL)
-- ---------------------------------------------------------------------------
CREATE SEQUENCE authcache_seq;
CREATE SEQUENCE caconnector_seq;
CREATE SEQUENCE challenge_seq;
CREATE SEQUENCE clientapp_seq;
CREATE SEQUENCE eventcounter_seq;
CREATE SEQUENCE eventhandler_seq;
CREATE SEQUENCE machineresolver_seq;
CREATE SEQUENCE monitoringstats_seq;
CREATE SEQUENCE pwreset_seq;
CREATE SEQUENCE periodictask_seq;
CREATE SEQUENCE audit_seq;
CREATE SEQUENCE policy_seq;
CREATE SEQUENCE privacyideaserver_seq;
CREATE SEQUENCE radiusserver_seq;
CREATE SEQUENCE realm_seq;
CREATE SEQUENCE resolver_seq;
CREATE SEQUENCE serviceid_seq;
CREATE SEQUENCE smsgateway_seq;
CREATE SEQUENCE smtpserver_seq;
CREATE SEQUENCE subscription_seq;
CREATE SEQUENCE token_seq;
CREATE SEQUENCE tokengroup_seq;
CREATE SEQUENCE usercache_seq;
CREATE SEQUENCE caconfig_seq;
CREATE SEQUENCE customuserattribute_seq;
CREATE SEQUENCE eventhandlercond_seq;
CREATE SEQUENCE eventhandleropt_seq;
CREATE SEQUENCE machineresolverconf_seq;
CREATE SEQUENCE machinetoken_seq;
CREATE SEQUENCE periodictasklastrun_seq;
CREATE SEQUENCE periodictaskopt_seq;
CREATE SEQUENCE policycondition_seq;
CREATE SEQUENCE resolverconf_seq;
CREATE SEQUENCE resolverrealm_seq;
CREATE SEQUENCE smsgwoption_seq;
CREATE SEQUENCE tokeninfo_seq;
CREATE SEQUENCE tokenowner_seq;
CREATE SEQUENCE tokenrealm_seq;
CREATE SEQUENCE tokentokengroup_seq;
CREATE SEQUENCE machtokenopt_seq;

-- ---------------------------------------------------------------------------
-- Tables (no FK dependencies first)
-- ---------------------------------------------------------------------------

CREATE TABLE admin (
    username VARCHAR(120) NOT NULL,
    password VARCHAR(255),
    email    VARCHAR(255),
    PRIMARY KEY (username)
);

CREATE TABLE config (
    "Key"         VARCHAR(255) NOT NULL,
    "Value"        VARCHAR(2000),
    "Type"         VARCHAR(2000),
    "Description"  VARCHAR(2000),
    PRIMARY KEY ("Key")
);

CREATE TABLE realm (
    id        INTEGER NOT NULL DEFAULT nextval('realm_seq'),
    name      VARCHAR(255) NOT NULL,
    "default" BOOLEAN,
    option    VARCHAR(40),
    PRIMARY KEY (id),
    UNIQUE (name)
);

CREATE TABLE resolver (
    id    INTEGER NOT NULL DEFAULT nextval('resolver_seq'),
    name  VARCHAR(255) NOT NULL,
    rtype VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name)
);

CREATE TABLE caconnector (
    id     INTEGER NOT NULL DEFAULT nextval('caconnector_seq'),
    name   VARCHAR(255) NOT NULL,
    catype VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name)
);

CREATE TABLE eventhandler (
    id            INTEGER NOT NULL DEFAULT nextval('eventhandler_seq'),
    name          VARCHAR(64),
    active        BOOLEAN,
    ordering      INTEGER NOT NULL,
    position      VARCHAR(10),
    event         VARCHAR(255) NOT NULL,
    handlermodule VARCHAR(255) NOT NULL,
    condition     VARCHAR(1024),
    action        VARCHAR(1024),
    PRIMARY KEY (id)
);

CREATE TABLE machineresolver (
    id    INTEGER NOT NULL DEFAULT nextval('machineresolver_seq'),
    name  VARCHAR(255) NOT NULL,
    rtype VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name)
);

CREATE TABLE monitoringstats (
    id          INTEGER NOT NULL DEFAULT nextval('monitoringstats_seq'),
    timestamp   TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    stats_key   VARCHAR(128) NOT NULL,
    stats_value INTEGER NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT msix_1 UNIQUE (timestamp, stats_key)
);

CREATE TABLE passwordreset (
    id           INTEGER NOT NULL DEFAULT nextval('pwreset_seq'),
    recoverycode VARCHAR(255) NOT NULL,
    username     VARCHAR(64) NOT NULL,
    realm        VARCHAR(64) NOT NULL,
    resolver     VARCHAR(64),
    email        VARCHAR(255),
    timestamp    TIMESTAMP WITHOUT TIME ZONE,
    expiration   TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id)
);

CREATE TABLE periodictask (
    id              INTEGER NOT NULL DEFAULT nextval('periodictask_seq'),
    name            VARCHAR(64) NOT NULL,
    active          BOOLEAN NOT NULL,
    retry_if_failed BOOLEAN NOT NULL,
    interval        VARCHAR(256) NOT NULL,
    nodes           VARCHAR(256) NOT NULL,
    taskmodule      VARCHAR(256) NOT NULL,
    ordering        INTEGER NOT NULL,
    last_update     TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name)
);

CREATE TABLE pidea_audit (
    id                 INTEGER NOT NULL DEFAULT nextval('audit_seq'),
    date               TIMESTAMP WITHOUT TIME ZONE,
    startdate          TIMESTAMP WITHOUT TIME ZONE,
    duration           INTERVAL,
    signature          VARCHAR(620),
    action             VARCHAR(50),
    success            INTEGER,
    serial             VARCHAR(40),
    token_type         VARCHAR(12),
    "user"             VARCHAR(20),
    realm              VARCHAR(20),
    resolver           VARCHAR(50),
    administrator      VARCHAR(20),
    action_detail      VARCHAR(50),
    info               VARCHAR(50),
    privacyidea_server VARCHAR(255),
    client             VARCHAR(50),
    loglevel           VARCHAR(12),
    clearance_level    VARCHAR(12),
    thread_id          VARCHAR(20),
    policies           VARCHAR(255),
    PRIMARY KEY (id)
);

CREATE TABLE policy (
    id                  INTEGER NOT NULL DEFAULT nextval('policy_seq'),
    active              BOOLEAN,
    check_all_resolvers BOOLEAN,
    name                VARCHAR(64) NOT NULL,
    scope               VARCHAR(32) NOT NULL,
    action              VARCHAR(2000),
    realm               VARCHAR(256),
    adminrealm          VARCHAR(256),
    adminuser           VARCHAR(256),
    resolver            VARCHAR(256),
    pinode              VARCHAR(256),
    "user"              VARCHAR(256),
    client              VARCHAR(256),
    time                VARCHAR(64),
    priority            INTEGER NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name)
);

CREATE TABLE privacyideaserver (
    id          INTEGER NOT NULL DEFAULT nextval('privacyideaserver_seq'),
    identifier  VARCHAR(255) NOT NULL,
    url         VARCHAR(255) NOT NULL,
    tls         BOOLEAN,
    description VARCHAR(2000),
    PRIMARY KEY (id),
    UNIQUE (identifier)
);

CREATE TABLE radiusserver (
    id          INTEGER NOT NULL DEFAULT nextval('radiusserver_seq'),
    identifier  VARCHAR(255) NOT NULL,
    server      VARCHAR(255) NOT NULL,
    port        INTEGER,
    secret      VARCHAR(255),
    dictionary  VARCHAR(255),
    description VARCHAR(2000),
    timeout     INTEGER,
    retries     INTEGER,
    PRIMARY KEY (id),
    UNIQUE (identifier)
);

CREATE TABLE serviceid (
    id            INTEGER NOT NULL DEFAULT nextval('serviceid_seq'),
    name          VARCHAR(255) NOT NULL,
    "Description" VARCHAR(2000),
    PRIMARY KEY (id),
    UNIQUE (name)
);

CREATE TABLE smsgateway (
    id             INTEGER NOT NULL DEFAULT nextval('smsgateway_seq'),
    identifier     VARCHAR(255) NOT NULL,
    description    VARCHAR(1024),
    providermodule VARCHAR(1024) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (identifier)
);

CREATE TABLE smtpserver (
    id          INTEGER NOT NULL DEFAULT nextval('smtpserver_seq'),
    identifier  VARCHAR(255) NOT NULL,
    server      VARCHAR(255) NOT NULL,
    port        INTEGER,
    username    VARCHAR(255),
    password    VARCHAR(255),
    sender      VARCHAR(255),
    tls         BOOLEAN,
    description VARCHAR(2000),
    timeout     INTEGER,
    enqueue_job BOOLEAN NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE subscription (
    id          INTEGER NOT NULL DEFAULT nextval('subscription_seq'),
    application VARCHAR(80),
    for_name    VARCHAR(80) NOT NULL,
    for_address VARCHAR(128),
    for_email   VARCHAR(128) NOT NULL,
    for_phone   VARCHAR(50) NOT NULL,
    for_url     VARCHAR(80),
    for_comment VARCHAR(255),
    by_name     VARCHAR(50) NOT NULL,
    by_email    VARCHAR(128) NOT NULL,
    by_address  VARCHAR(128),
    by_phone    VARCHAR(50),
    by_url      VARCHAR(80),
    date_from   TIMESTAMP WITHOUT TIME ZONE,
    date_till   TIMESTAMP WITHOUT TIME ZONE,
    num_users   INTEGER,
    num_tokens  INTEGER,
    num_clients INTEGER,
    level       VARCHAR(80),
    signature   VARCHAR(640),
    PRIMARY KEY (id)
);

CREATE TABLE token (
    id            INTEGER NOT NULL DEFAULT nextval('token_seq'),
    description   VARCHAR(80),
    serial        VARCHAR(40) NOT NULL,
    tokentype     VARCHAR(30),
    user_pin      VARCHAR(512),
    user_pin_iv   VARCHAR(32),
    so_pin        VARCHAR(512),
    so_pin_iv     VARCHAR(32),
    pin_seed      VARCHAR(32),
    otplen        INTEGER,
    pin_hash      VARCHAR(512),
    key_enc       VARCHAR(2800),
    key_iv        VARCHAR(32),
    maxfail       INTEGER,
    active        BOOLEAN NOT NULL,
    revoked       BOOLEAN,
    locked        BOOLEAN,
    failcount     INTEGER,
    count         INTEGER,
    count_window  INTEGER,
    sync_window   INTEGER,
    rollout_state VARCHAR(10),
    PRIMARY KEY (id),
    UNIQUE (serial)
);

CREATE TABLE tokengroup (
    id            INTEGER NOT NULL DEFAULT nextval('tokengroup_seq'),
    name          VARCHAR(255) NOT NULL,
    "Description" VARCHAR(2000),
    PRIMARY KEY (id),
    UNIQUE (name)
);

CREATE TABLE usercache (
    id         INTEGER NOT NULL DEFAULT nextval('usercache_seq'),
    username   VARCHAR(64),
    used_login VARCHAR(64),
    resolver   VARCHAR(120),
    user_id    VARCHAR(320),
    timestamp  TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id)
);

CREATE TABLE authcache (
    id             INTEGER NOT NULL DEFAULT nextval('authcache_seq'),
    first_auth     TIMESTAMP WITHOUT TIME ZONE,
    last_auth      TIMESTAMP WITHOUT TIME ZONE,
    username       VARCHAR(64),
    resolver       VARCHAR(120),
    realm          VARCHAR(120),
    client_ip      VARCHAR(40),
    user_agent     VARCHAR(120),
    auth_count     INTEGER,
    authentication VARCHAR(255),
    PRIMARY KEY (id)
);

CREATE TABLE challenge (
    id             INTEGER NOT NULL DEFAULT nextval('challenge_seq'),
    transaction_id VARCHAR(64) NOT NULL,
    data           VARCHAR(512),
    challenge      VARCHAR(512),
    "session"      VARCHAR(512),
    serial         VARCHAR(40),
    timestamp      TIMESTAMP WITHOUT TIME ZONE,
    expiration     TIMESTAMP WITHOUT TIME ZONE,
    received_count INTEGER,
    otp_valid      BOOLEAN,
    PRIMARY KEY (id)
);

CREATE TABLE clientapplication (
    id         INTEGER NOT NULL DEFAULT nextval('clientapp_seq'),
    ip         VARCHAR(255) NOT NULL,
    hostname   VARCHAR(255),
    clienttype VARCHAR(255) NOT NULL,
    lastseen   TIMESTAMP WITHOUT TIME ZONE,
    node       VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT caix UNIQUE (ip, clienttype, node)
);

CREATE TABLE eventcounter (
    id            INTEGER NOT NULL DEFAULT nextval('eventcounter_seq'),
    counter_name  VARCHAR(80) NOT NULL,
    counter_value INTEGER,
    node          VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT evctr_1 UNIQUE (counter_name, node)
);

-- ---------------------------------------------------------------------------
-- Tables with FK dependencies
-- ---------------------------------------------------------------------------

CREATE TABLE caconnectorconfig (
    id             INTEGER NOT NULL DEFAULT nextval('caconfig_seq'),
    caconnector_id INTEGER,
    "Key"          VARCHAR(255) NOT NULL,
    "Value"        VARCHAR(2000),
    "Type"         VARCHAR(2000),
    "Description"  VARCHAR(2000),
    PRIMARY KEY (id),
    CONSTRAINT ccix_2 UNIQUE (caconnector_id, "Key"),
    FOREIGN KEY (caconnector_id) REFERENCES caconnector (id)
);

CREATE TABLE customuserattribute (
    id       INTEGER NOT NULL DEFAULT nextval('customuserattribute_seq'),
    user_id  VARCHAR(320),
    resolver VARCHAR(120),
    realm_id INTEGER,
    "Key"    VARCHAR(255) NOT NULL,
    "Value"  TEXT,
    "Type"   VARCHAR(100),
    PRIMARY KEY (id),
    FOREIGN KEY (realm_id) REFERENCES realm (id)
);

CREATE TABLE eventhandlercondition (
    id              INTEGER NOT NULL DEFAULT nextval('eventhandlercond_seq'),
    eventhandler_id INTEGER,
    "Key"           VARCHAR(255) NOT NULL,
    "Value"         VARCHAR(2000),
    comparator      VARCHAR(255),
    PRIMARY KEY (id),
    CONSTRAINT ehcix_1 UNIQUE (eventhandler_id, "Key"),
    FOREIGN KEY (eventhandler_id) REFERENCES eventhandler (id)
);

CREATE TABLE eventhandleroption (
    id              INTEGER NOT NULL DEFAULT nextval('eventhandleropt_seq'),
    eventhandler_id INTEGER,
    "Key"           VARCHAR(255) NOT NULL,
    "Value"         VARCHAR(2000),
    "Type"          VARCHAR(2000),
    "Description"   VARCHAR(2000),
    PRIMARY KEY (id),
    CONSTRAINT ehoix_1 UNIQUE (eventhandler_id, "Key"),
    FOREIGN KEY (eventhandler_id) REFERENCES eventhandler (id)
);

CREATE TABLE machineresolverconfig (
    id          INTEGER NOT NULL DEFAULT nextval('machineresolverconf_seq'),
    resolver_id INTEGER,
    "Key"       VARCHAR(255) NOT NULL,
    "Value"     VARCHAR(2000),
    "Type"      VARCHAR(2000),
    "Description" VARCHAR(2000),
    PRIMARY KEY (id),
    CONSTRAINT mrcix_2 UNIQUE (resolver_id, "Key"),
    FOREIGN KEY (resolver_id) REFERENCES machineresolver (id)
);

CREATE TABLE machinetoken (
    id                 INTEGER NOT NULL DEFAULT nextval('machinetoken_seq'),
    token_id           INTEGER,
    machineresolver_id INTEGER,
    machine_id         VARCHAR(255),
    application        VARCHAR(64),
    PRIMARY KEY (id),
    FOREIGN KEY (token_id) REFERENCES token (id)
);

CREATE TABLE machinetokenoptions (
    id              INTEGER NOT NULL DEFAULT nextval('machtokenopt_seq'),
    machinetoken_id INTEGER,
    mt_key          VARCHAR(64) NOT NULL,
    mt_value        VARCHAR(64) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (machinetoken_id) REFERENCES machinetoken (id)
);

CREATE TABLE periodictasklastrun (
    id              INTEGER NOT NULL DEFAULT nextval('periodictasklastrun_seq'),
    periodictask_id INTEGER,
    node            VARCHAR(255) NOT NULL,
    timestamp       TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ptlrix_1 UNIQUE (periodictask_id, node),
    FOREIGN KEY (periodictask_id) REFERENCES periodictask (id)
);

CREATE TABLE periodictaskoption (
    id              INTEGER NOT NULL DEFAULT nextval('periodictaskopt_seq'),
    periodictask_id INTEGER,
    key             VARCHAR(255) NOT NULL,
    value           VARCHAR(2000),
    PRIMARY KEY (id),
    CONSTRAINT ptoix_1 UNIQUE (periodictask_id, key),
    FOREIGN KEY (periodictask_id) REFERENCES periodictask (id)
);

CREATE TABLE policycondition (
    id         INTEGER NOT NULL DEFAULT nextval('policycondition_seq'),
    policy_id  INTEGER NOT NULL,
    section    VARCHAR(255) NOT NULL,
    "Key"      VARCHAR(255) NOT NULL,
    comparator VARCHAR(255) NOT NULL,
    "Value"    VARCHAR(2000) NOT NULL,
    active     BOOLEAN NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (policy_id) REFERENCES policy (id)
);

CREATE TABLE resolverconfig (
    id          INTEGER NOT NULL DEFAULT nextval('resolverconf_seq'),
    resolver_id INTEGER,
    "Key"       VARCHAR(255) NOT NULL,
    "Value"     VARCHAR(2000),
    "Type"      VARCHAR(2000),
    "Description" VARCHAR(2000),
    PRIMARY KEY (id),
    CONSTRAINT rcix_2 UNIQUE (resolver_id, "Key"),
    FOREIGN KEY (resolver_id) REFERENCES resolver (id)
);

CREATE TABLE resolverrealm (
    id          INTEGER NOT NULL DEFAULT nextval('resolverrealm_seq'),
    resolver_id INTEGER,
    realm_id    INTEGER,
    priority    INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT rrix_2 UNIQUE (resolver_id, realm_id),
    FOREIGN KEY (resolver_id) REFERENCES resolver (id),
    FOREIGN KEY (realm_id)    REFERENCES realm (id)
);

CREATE TABLE smsgatewayoption (
    id         INTEGER NOT NULL DEFAULT nextval('smsgwoption_seq'),
    "Key"      VARCHAR(255) NOT NULL,
    "Value"    TEXT,
    "Type"     VARCHAR(100),
    gateway_id INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT sgix_1 UNIQUE (gateway_id, "Key", "Type"),
    FOREIGN KEY (gateway_id) REFERENCES smsgateway (id)
);

CREATE TABLE tokeninfo (
    id            INTEGER NOT NULL DEFAULT nextval('tokeninfo_seq'),
    "Key"         VARCHAR(255) NOT NULL,
    "Value"       TEXT,
    "Type"        VARCHAR(100),
    "Description" VARCHAR(2000),
    token_id      INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT tiix_2 UNIQUE (token_id, "Key"),
    FOREIGN KEY (token_id) REFERENCES token (id)
);

CREATE TABLE tokenowner (
    id       INTEGER NOT NULL DEFAULT nextval('tokenowner_seq'),
    token_id INTEGER,
    resolver VARCHAR(120),
    user_id  VARCHAR(320),
    realm_id INTEGER,
    PRIMARY KEY (id),
    FOREIGN KEY (token_id) REFERENCES token (id),
    FOREIGN KEY (realm_id) REFERENCES realm (id)
);

CREATE TABLE tokenrealm (
    id       INTEGER DEFAULT nextval('tokenrealm_seq'),
    token_id INTEGER,
    realm_id INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT trix_2 UNIQUE (token_id, realm_id),
    FOREIGN KEY (token_id) REFERENCES token (id),
    FOREIGN KEY (realm_id) REFERENCES realm (id)
);

CREATE TABLE tokentokengroup (
    id            INTEGER DEFAULT nextval('tokentokengroup_seq'),
    token_id      INTEGER,
    tokengroup_id INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT ttgix_2 UNIQUE (token_id, tokengroup_id),
    FOREIGN KEY (token_id)      REFERENCES token (id),
    FOREIGN KEY (tokengroup_id) REFERENCES tokengroup (id)
);

-- ---------------------------------------------------------------------------
-- Data
-- ---------------------------------------------------------------------------

INSERT INTO config ("Key", "Value", "Type", "Description") VALUES
    ('PI_PEPPER',          'dGVzdHBlcHBlcg==', 'password', 'Pepper for hashing'),
    ('DefaultOtpLen',      '6',                '',         ''),
    ('DefaultMaxFailCount','10',               '',         ''),
    ('__timestamp__',      '1680000000',       '',         'config timestamp. last changed.');

INSERT INTO realm (id, name, "default") VALUES
    (1, 'defrealm',  TRUE),
    (2, 'testrealm', FALSE);

SELECT setval('realm_seq', 2);

INSERT INTO resolver (id, name, rtype) VALUES
    (1, 'defresolver', 'passwdresolver');

SELECT setval('resolver_seq', 1);

INSERT INTO resolverconfig (id, resolver_id, "Key", "Value") VALUES
    (1, 1, 'fileName', '/etc/passwd');

SELECT setval('resolverconf_seq', 1);

INSERT INTO resolverrealm (id, resolver_id, realm_id, priority) VALUES
    (1, 1, 1, 1),
    (2, 1, 2, 1);

SELECT setval('resolverrealm_seq', 2);

INSERT INTO token (id, serial, tokentype, otplen, active, key_enc, key_iv, pin_hash) VALUES
    (1, 'HOTP0001', 'hotp', 6, TRUE, 'aabbccddeeff00112233445566778899aabbccddeeff001122334455', '00112233445566778899aabbccdd0011', '$pbkdf2-sha512$...fakehash...'),
    (2, 'TOTP0001', 'totp', 6, TRUE, 'aabbccddeeff00112233445566778899aabbccddeeff001122334455', '00112233445566778899aabbccdd0022', ''),
    (3, 'PIPU0001', 'push', 6, TRUE, '', '', '');

SELECT setval('token_seq', 3);

INSERT INTO tokeninfo (id, token_id, "Key", "Value") VALUES
    (1, 2, 'timeStep',              '30'),
    (2, 2, 'timeWindow',            '180'),
    (3, 3, 'firebase_config',       'myFirebase'),
    (4, 3, 'public_key_smartphone', 'fakePublicKey==');

SELECT setval('tokeninfo_seq', 4);

INSERT INTO tokenowner (id, token_id, resolver, user_id, realm_id) VALUES
    (1, 1, 'defresolver', '1000', 1),
    (2, 2, 'defresolver', '1000', 1);

SELECT setval('tokenowner_seq', 2);

INSERT INTO tokenrealm (id, token_id, realm_id) VALUES
    (1, 1, 1),
    (2, 2, 1),
    (3, 3, 1);

SELECT setval('tokenrealm_seq', 3);

INSERT INTO tokengroup (id, name, "Description") VALUES
    (1, 'vpn-tokens',   'Tokens used for VPN access'),
    (2, 'admin-tokens', 'Tokens for administrators');

SELECT setval('tokengroup_seq', 2);

INSERT INTO tokentokengroup (id, token_id, tokengroup_id) VALUES
    (1, 1, 1),
    (2, 2, 2);

SELECT setval('tokentokengroup_seq', 2);

INSERT INTO policy (id, active, name, scope, action, realm, priority) VALUES
    (1, TRUE,  'superuser',         'admin',  'superuser',         '',        1),
    (2, TRUE,  'enroll-hotp',       'enroll', 'enrollHOTP',        'defrealm',1),
    (3, TRUE,  'no-detail-on-fail', 'authz',  'no_detail_on_fail', '',        1),
    (4, FALSE, 'disabled-policy',   'auth',   'push_wait=20',      '',        1);

SELECT setval('policy_seq', 4);

INSERT INTO policycondition (id, policy_id, section, "Key", comparator, "Value", active) VALUES
    (1, 2, 'userinfo', 'memberOf', 'equals', 'cn=vpn,dc=example,dc=com', TRUE);

SELECT setval('policycondition_seq', 1);

INSERT INTO admin (username, password, email) VALUES
    ('admin', '$pbkdf2-sha512$25000$fakesalt$fakehash==', 'admin@example.com');

INSERT INTO smsgateway (id, identifier, description, providermodule) VALUES
    (1, 'myFirebase', 'Firebase push gateway', 'privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider');

SELECT setval('smsgateway_seq', 1);

INSERT INTO smsgatewayoption (id, gateway_id, "Key", "Value", "Type") VALUES
    (1, 1, 'FIREBASE_CONFIG', '/etc/privacyidea/firebase.json', 'option'),
    (2, 1, 'PROJECT_ID',      'my-firebase-project',            'option');

SELECT setval('smsgwoption_seq', 2);

INSERT INTO eventhandler (id, name, active, ordering, position, event, handlermodule, action) VALUES
    (1, 'send-email-on-fail', TRUE, 0, 'post', 'validate_check', 'privacyidea.lib.eventhandler.EmailEventHandler', 'sendmail');

SELECT setval('eventhandler_seq', 1);

INSERT INTO eventhandleroption (id, eventhandler_id, "Key", "Value") VALUES
    (1, 1, 'body',    'Authentication failed for {user}'),
    (2, 1, 'subject', 'privacyIDEA authentication failure');

SELECT setval('eventhandleropt_seq', 2);

INSERT INTO eventhandlercondition (id, eventhandler_id, "Key", "Value", comparator) VALUES
    (1, 1, 'result_value', 'False', 'equal');

SELECT setval('eventhandlercond_seq', 1);

INSERT INTO smtpserver (id, identifier, server, port, sender, tls, enqueue_job) VALUES
    (1, 'default-smtp', 'mail.example.com', 587, 'noreply@example.com', TRUE, FALSE);

SELECT setval('smtpserver_seq', 1);

INSERT INTO clientapplication (id, ip, hostname, clienttype, node) VALUES
    (1, '10.0.0.1', 'vpnclient.example.com', 'PAM',    'pinode1'),
    (2, '10.0.0.2', 'webserver.example.com', 'OAUTH2', 'pinode1');

SELECT setval('clientapp_seq', 2);

INSERT INTO customuserattribute (id, user_id, resolver, realm_id, "Key", "Value") VALUES
    (1, '1000', 'defresolver', 1, 'department', 'engineering');

SELECT setval('customuserattribute_seq', 1);

INSERT INTO serviceid (id, name, "Description") VALUES
    (1, 'ssh-servers', 'SSH key consumers');

SELECT setval('serviceid_seq', 1);

INSERT INTO eventcounter (id, counter_name, counter_value, node) VALUES
    (1, 'failed_auth', 42, 'pinode1'),
    (2, 'failed_auth', 17, 'pinode2');

SELECT setval('eventcounter_seq', 2);

INSERT INTO periodictask (id, name, active, retry_if_failed, interval, nodes, taskmodule, ordering, last_update) VALUES
    (1, 'cleanup-audit', TRUE, TRUE, '0 2 * * *', 'pinode1', 'privacyidea.lib.periodictask.AuditCleanup', 0, '2023-01-01 02:00:00');

SELECT setval('periodictask_seq', 1);

INSERT INTO periodictaskoption (id, periodictask_id, key, value) VALUES
    (1, 1, 'age', '180d');

SELECT setval('periodictaskopt_seq', 1);

INSERT INTO periodictasklastrun (id, periodictask_id, node, timestamp) VALUES
    (1, 1, 'pinode1', '2023-06-01 02:00:00');

SELECT setval('periodictasklastrun_seq', 1);

INSERT INTO monitoringstats (id, timestamp, stats_key, stats_value) VALUES
    (1, '2023-06-01 00:00:00', 'token_count',  47),
    (2, '2023-06-01 00:00:00', 'active_users', 39);

SELECT setval('monitoringstats_seq', 2);

INSERT INTO pidea_audit (id, date, action, success, serial, token_type, "user", realm, administrator, client, loglevel, clearance_level, thread_id) VALUES
    (1, '2023-06-01 10:00:00', 'validate/check', 1, 'HOTP0001', 'hotp', 'alice', 'defrealm', '', '10.0.0.1', 'INFO', 'default', '12345'),
    (2, '2023-06-01 10:01:00', 'validate/check', 0, 'TOTP0001', 'totp', 'alice', 'defrealm', '', '10.0.0.1', 'INFO', 'default', '12346');

SELECT setval('audit_seq', 2);

-- ---------------------------------------------------------------------------
-- alembic_version — stamp the DB at START_REVISION
-- ---------------------------------------------------------------------------
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num) VALUES ('5cb310101a1f');
