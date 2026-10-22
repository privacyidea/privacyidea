"""
The data the system documentation is rendered from: selected settings of the configuration and statistics.
"""
from sqlalchemy import text

from privacyidea.lib.caconnector import delete_caconnector
from privacyidea.lib.crypto import CENSORED
from privacyidea.lib.event import delete_event, set_event
from privacyidea.lib.machine import attach_token
from privacyidea.lib.machineresolver import delete_resolver as delete_machine_resolver
from privacyidea.lib.machineresolver import save_resolver as save_machine_resolver
from privacyidea.lib.radiusserver import add_radius, delete_radius
from privacyidea.lib.smsprovider.SMSProvider import delete_smsgateway, set_smsgateway
from privacyidea.lib.smtpserver import add_smtpserver, delete_smtpserver
from privacyidea.lib.system_documentation import (_get_sms_provider_parameters, get_app_config_for_documentation,
                                                  get_caconnectors_for_documentation,
                                                  get_events_for_documentation, get_machines_for_documentation,
                                                  get_radiusservers_for_documentation, get_schema_revision,
                                                  get_smsgateways_for_documentation,
                                                  get_smtpservers_for_documentation, get_token_statistics)
from privacyidea.lib.container import delete_container_by_serial, init_container
from privacyidea.lib.token import enable_token, init_token, remove_token
from privacyidea.lib.user import User
from privacyidea.models import CAConnector, db
from .base import MyTestCase


class SystemDocumentationTestCase(MyTestCase):

    def test_01_app_config(self):
        app_config = {
            "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg2://pi:database-password@db.example.com/pi",
            "PI_AUDIT_SQL_URI": "mysql+pymysql://pi:audit-password@audit.example.com/pi",
            "PI_REDIS_URL": "redis://:redis-password@redis.example.com:6379/0",
            "PI_TRUSTED_JWT": [{"public_key": "a-public-key"}, {"public_key": "another-public-key"}],
            "PI_HSM_MODULE": "privacyidea.lib.security.aeshsm.AESHardwareSecurityModule",
            "PI_HSM_MODULE_PASSWORD": "hsm-password",
            "PI_ENCFILE": "/etc/privacyidea/enckey",
            "PI_MYPLUGIN_SETTING": "plugin-value",
            "SUPERUSER_REALM": ["admins"],
            "PI_NO_RESPONSE_SIGN": True,
        }
        documented = get_app_config_for_documentation(app_config)

        self.assertEqual({"SUPERUSER_REALM": ["admins"],
                          "PI_NO_RESPONSE_SIGN": True,
                          "PI_HSM_MODULE": "privacyidea.lib.security.aeshsm.AESHardwareSecurityModule",
                          # A connect string is documented by its driver, a URL by whether it is set
                          "SQLALCHEMY_DATABASE_URI (driver)": "postgresql+psycopg2",
                          "PI_AUDIT_SQL_URI (driver)": "mysql+pymysql",
                          "PI_REDIS_URL (set)": True,
                          "PI_BASE_URL (set)": False,
                          "PI_TRUSTED_JWT (entries)": 2}, documented)
        # A connect string that can not be read is documented without its content
        documented = get_app_config_for_documentation({"PI_AUDIT_SQL_URI": "no connect string"})
        self.assertEqual("unknown", documented["PI_AUDIT_SQL_URI (driver)"])

    def test_02_events(self):
        self.setUp_user_realms()
        notification_id = set_event("notify", ["token_init", "token_assign"], "UserNotification", "sendmail",
                                    conditions={"tokentype": "hotp,totp", "realm": self.realm1,
                                                "serial": "^HOTP.*$", "tokeninfo": "email==someone@example.com",
                                                "count_auth": "<100"},
                                    options={"To": "tokenowner", "mimetype": "html", "subject": "Welcome",
                                             "body": "The token of {user} is enrolled", "attach_qrcode": "1"})
        webhook_id = set_event("hook", ["validate_check"], "WebHook", "post_webhook", position="pre",
                               conditions={"result_value": "False", "tokentype": "hotp,unknown-type"},
                               options={"URL": "https://hooks.example.com/static-hook-token",
                                        "content_type": "not-a-content-type", "replace": "False"})
        # An event handler whose module is not available is documented without the values of its settings
        unknown_id = set_event("unknown", ["token_init"], "NotAvailable", "do", options={"setting": "value"})
        try:
            documented = {event["name"]: event for event in get_events_for_documentation()}

            # A value that is one of the choices the handler declares, a bool or a number is documented
            self.assertEqual({"name": "notify", "handlermodule": "UserNotification", "active": True,
                              "position": "post", "ordering": 0, "event": ["token_init", "token_assign"],
                              "action": "sendmail", "abort_on_error": False,
                              "conditions": {"tokentype": "hotp,totp", "realm": self.realm1, "serial": CENSORED,
                                             "tokeninfo": CENSORED, "count_auth": CENSORED},
                              "options": {"To": "tokenowner", "mimetype": "html", "subject": CENSORED,
                                          "body": CENSORED, "attach_qrcode": True}},
                             documented["notify"])
            # A value that is not one of the declared choices is censored, also in a selection of several
            self.assertEqual({"result_value": "False", "tokentype": CENSORED}, documented["hook"]["conditions"])
            self.assertEqual({"URL": CENSORED, "content_type": CENSORED, "replace": False},
                             documented["hook"]["options"])
            self.assertEqual("pre", documented["hook"]["position"])
            self.assertEqual({"setting": CENSORED}, documented["unknown"]["options"])
        finally:
            for event_id in (notification_id, webhook_id, unknown_id):
                delete_event(event_id)

    def test_03_smtpservers(self):
        add_smtpserver("mailserver", "mail.example.com", port=587, username="mail-account", password="mail-password",
                       sender="privacyidea@example.com", tls=True)
        try:
            documented = get_smtpservers_for_documentation()
        finally:
            delete_smtpserver("mailserver")
        # The server is documented by how it is connected, not by the host, the sender or the account
        self.assertEqual([{"identifier": "mailserver", "port": 587, "tls": True, "authentication": True,
                           "smime": False, "timeout": 10}], documented)

    def test_04_radiusservers(self):
        add_radius("radiusserver", "radius.example.com", "shared-secret", port=1812, retries=2, timeout=3,
                   options={"message_authenticator": True})
        try:
            documented = get_radiusservers_for_documentation()
        finally:
            delete_radius("radiusserver")
        self.assertEqual([{"identifier": "radiusserver", "port": 1812, "timeout": 3, "retries": 2,
                           "message_authenticator": True}], documented)

    def test_05_smsgateways(self):
        set_smsgateway("smsgateway", "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",
                       options={"URL": "https://sms.example.com/send?key=gateway-key", "HTTP_METHOD": "POST",
                                "CHECK_SSL": "yes", "SEND_DATA_AS_JSON": "maybe", "PASSWORD": "gateway-password",
                                "sender": "privacyIDEA"},
                       headers={"Authorization": "Bearer gateway-token"})
        try:
            documented = get_smsgateways_for_documentation()
        finally:
            delete_smsgateway("smsgateway")
        # A value that is one of the choices the provider declares is documented, every other option and every
        # header is censored
        self.assertEqual([{"identifier": "smsgateway",
                           "providermodule": "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",
                           "options": {"URL": CENSORED, "HTTP_METHOD": "POST", "CHECK_SSL": "yes",
                                       "SEND_DATA_AS_JSON": CENSORED, "PASSWORD": CENSORED, "sender": CENSORED},
                           "headers": {"Authorization": CENSORED}}], documented)
        # A provider that does not ship with privacyIDEA is not imported, its options are all censored
        self.assertEqual({}, _get_sms_provider_parameters("custom.provider.CustomSMSProvider"))

    def test_06_caconnectors(self):
        CAConnector("localca", "local").save()
        try:
            self.assertEqual([{"name": "localca", "type": "local"}], get_caconnectors_for_documentation())
        finally:
            delete_caconnector("localca")

    def test_07_machines(self):
        save_machine_resolver({"name": "hostsresolver", "type": "hosts", "filename": "tests/testdata/hosts"})
        token = init_token({"type": "hotp", "genkey": 1, "serial": "DOCHOTP01"})
        attach_token(token.token.serial, "offline")
        try:
            self.assertEqual({"resolvers": [{"name": "hostsresolver", "type": "hosts"}],
                              "attachments": {"offline": 1}},
                             get_machines_for_documentation())
        finally:
            remove_token("DOCHOTP01")
            delete_machine_resolver("hostsresolver")

    def test_08_token_statistics(self):
        self.setUp_user_realms()
        init_token({"type": "hotp", "genkey": 1, "serial": "DOCHOTP01"}, user=User("cornelius", self.realm1))
        init_token({"type": "hotp", "genkey": 1, "serial": "DOCHOTP02"})
        enable_token("DOCHOTP02", enable=False)
        init_token({"type": "totp", "genkey": 1, "serial": "DOCTOTP01"})
        container_serial = init_container({"type": "smartphone"})["container_serial"]
        try:
            self.assertEqual({"tokens": {"hotp": {"total": 2, "active": 1, "assigned": 1},
                                         "totp": {"total": 1, "active": 1, "assigned": 0}},
                              "containers": {"smartphone": 1}},
                             get_token_statistics())
        finally:
            for serial in ("DOCHOTP01", "DOCHOTP02", "DOCTOTP01"):
                remove_token(serial)
            delete_container_by_serial(container_serial)

    def test_09_schema_revision(self):
        # The test database is created without the schema migrations, so it is not stamped
        self.assertEqual("unknown", get_schema_revision())
        db.session.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        try:
            db.session.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0123456789ab')"))
            self.assertEqual("0123456789ab", get_schema_revision())
        finally:
            db.session.execute(text("DROP TABLE alembic_version"))
            db.session.commit()
