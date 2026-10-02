"""v3.14.1: Store boolean policy actions saved with a false value as excluded actions

The policy matching only checks whether an action is set and ignores its value, so a boolean action saved with a value
like ``policywrite=False`` acted as enabled. The policy template "helpdesk" of the WebUI stored 21 admin rights like
this, which it meant to deny. Saving a policy now stores such an action as the excluded action ``-policywrite``, and
this migration does the same for the policies already stored.

Only the values ``false`` (in any case) and ``0`` are taken as false, since whoever stored them meant to disable the
action. Other values like ``triggerchallenge=hotp`` acted as enabled until now and are left as they are, the
migration logs them as warnings.

The boolean actions are a snapshot of the policy definitions of this version, so the migration does not depend on the
models of a later version. Boolean actions of token types outside privacyIDEA are not included, they are excluded the
next time the policy is saved.

The downgrade does not restore the values, the excluded action means the same in every version.

Revision ID: f8a498439814
Revises: b7c1e4d2a9f3
Create Date: 2026-10-02 15:00:00.000000

"""
import logging
import re

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm

log = logging.getLogger("alembic.env")

revision = 'f8a498439814'
down_revision = 'b7c1e4d2a9f3'
branch_labels = None
depends_on = None

FALSE_VALUES = ("false", "0")
TRUE_VALUES = ("1", "True", "true", "TRUE")

# The boolean actions of each scope in v3.14.1, including those of the token types privacyIDEA ships
BOOL_ACTIONS = {
    "authorization": frozenset({
        "add_resolver_in_response", "add_user_in_response", "api_key_required", "application_tokentype",
        "no_detail_on_fail", "no_detail_on_success", "require_auth_for_resolver_details"
    }),
    "admin": frozenset({
        "adduser", "api_client_add", "api_client_delete", "api_client_edit", "api_client_list", "api_client_rotate",
        "applspec_force_server_generate", "assign", "auditlog", "auditlog_download", "authentication_log_read",
        "blocklist_read", "blocklist_reset", "blocklist_set", "caconnectordelete", "caconnectorread",
        "caconnectorwrite", "cancelchallenge", "clienttype", "conditional_access_policy_read",
        "conditional_access_policy_write", "configdelete", "configread", "configwrite", "container_add_token",
        "container_assign_user", "container_create", "container_delete", "container_description", "container_info",
        "container_list", "container_realms", "container_register", "container_remove_token", "container_rollover",
        "container_state", "container_template_create", "container_template_delete", "container_template_list",
        "container_unassign_user", "container_unregister", "copytokenpin", "copytokenuser",
        "daypassword_force_server_generate", "delete", "deleteuser", "disable", "enable", "enroll4EYES",
        "enrollAPPLSPEC", "enrollCERTIFICATE", "enrollDAPLUG", "enrollDAYPASSWORD", "enrollEMAIL", "enrollHOTP",
        "enrollINDEXEDSECRET", "enrollMOTP", "enrollOCRA", "enrollPAPER", "enrollPASSKEY", "enrollPUSH", "enrollPW",
        "enrollQUESTION", "enrollRADIUS", "enrollREGISTRATION", "enrollREMOTE", "enrollSMS", "enrollSPASS",
        "enrollSSHKEY", "enrollTAN", "enrollTIQR", "enrollTOTP", "enrollVASCO", "enrollWEBAUTHN", "enrollYUBICO",
        "enrollYUBIKEY", "enrollpin", "eventhandling_read", "eventhandling_write", "fetch_authentication_items",
        "get_user_internal_attributes", "getchallenges", "getrandom", "getserial", "hotp_force_server_generate",
        "importtokens", "losttoken", "machinelist", "manage_machine_tokens", "managesubscription",
        "motp_force_server_generate", "mresolverdelete", "mresolverread", "mresolverwrite", "periodictask_read",
        "periodictask_write", "policydelete", "policyread", "policywrite", "privacyideaserver_read",
        "privacyideaserver_write", "radiusserver_read", "radiusserver_write", "remembered_device_list",
        "remembered_device_revoke", "reset", "resolverdelete", "resolverread", "resolverwrite", "resync", "revoke",
        "serviceid_add", "serviceid_delete", "serviceid_list", "set", "set_hsm_password", "setdescription", "setpin",
        "setrandompin", "settokeninfo", "smsgateway_read", "smsgateway_write", "smtpserver_read", "smtpserver_write",
        "sshkey_read", "statistics_delete", "statistics_read", "system_documentation", "token_rollover",
        "tokengroup_add", "tokengroup_delete", "tokengroup_list", "tokengroups", "tokenlist", "tokenrealms",
        "totp_force_server_generate", "triggerchallenge", "unassign", "updateuser", "user_lock_read",
        "user_lock_reset", "user_lock_set", "userlist"
    }),
    "authentication": frozenset({
        "change_pin_via_validate", "client_mode_per_user", "emailautosend", "enroll_via_multichallenge_optional",
        "enroll_via_multichallenge_passkey_offline", "force_challenge_response", "hide_specific_error_message",
        "increase_failcounter_on_challenge", "passOnNoToken", "passOnNoUser", "passkey_enforce_user_handle",
        "passkey_trigger_by_pin", "push_code_to_phone", "push_require_presence", "remember_device",
        "reset_all_user_tokens", "resync_via_multichallenge", "smsautosend"
    }),
    "user": frozenset({
        "applspec_force_server_generate", "assign", "auditlog", "authentication_log_read", "container_add_token",
        "container_assign_user", "container_create", "container_delete", "container_description", "container_list",
        "container_register", "container_remove_token", "container_rollover", "container_state",
        "container_template_create", "container_template_delete", "container_template_list",
        "container_unassign_user", "container_unregister", "daypassword_force_server_generate", "delete", "disable",
        "enable", "enrollAPPLSPEC", "enrollCERTIFICATE", "enrollDAYPASSWORD", "enrollEMAIL", "enrollHOTP",
        "enrollINDEXEDSECRET", "enrollMOTP", "enrollPAPER", "enrollPASSKEY", "enrollPUSH", "enrollQUESTION",
        "enrollRADIUS", "enrollSMS", "enrollSPASS", "enrollSSHKEY", "enrollTAN", "enrollTIQR", "enrollTOTP",
        "enrollWEBAUTHN", "enrollYUBICO", "enrollYUBIKEY", "enrollpin", "hotp_force_server_generate",
        "motp_force_server_generate", "password_reset", "reset", "resync", "revoke", "serviceid_list",
        "setdescription", "setpin", "setrandompin", "sshkey_read", "token_rollover", "totp_force_server_generate",
        "unassign", "updateuser", "userlist"
    }),
    "enrollment": frozenset({
        "change_pin_on_first_use", "daypassword_force_app_pin", "encrypt_pin", "hotp_force_app_pin",
        "push_force_app_pin", "push_use_pia_scheme", "totp_force_app_pin", "webauthn_avoid_double_registration"
    }),
    "webui": frozenset({
        "admin_dashboard", "container_wizard_registration", "deletion_confirmation", "dialog_no_token",
        "hide_buttons", "hide_welcome_info", "search_on_enter", "show_android_privacyidea_authenticator",
        "show_ios_privacyidea_authenticator", "show_node", "show_seed", "tokenwizard", "tokenwizard_2nd_token",
        "user_details"
    }),
    "register": frozenset({
        "hide_specific_error_message"
    }),
    "container": frozenset({
        "container_client_rollover", "disable_client_container_unregister", "disable_client_token_deletion",
        "hide_specific_error_message", "initially_add_tokens_to_container"
    }),
    "token": frozenset({
        "hide_specific_error_message_for_offline_refill", "hide_specific_error_message_for_ttype"
    }),
    "hardening": frozenset({
        "hide_auth_error_status", "hide_version"
    }),
    "conditional_access": frozenset({
        "show_default_ca_error_message"
    }),
}


Base = orm.declarative_base()


class Policy(Base):
    # Only the columns the migration reads or writes
    __tablename__ = "policy"
    id = sa.Column(sa.Integer, sa.Sequence("policy_seq"), primary_key=True)
    name = sa.Column(sa.Unicode(64))
    scope = sa.Column(sa.Unicode(32))
    action = sa.Column(sa.Text, default="")


def negate_false_bool_actions(scope: str, action: str) -> tuple[str, list[str]]:
    """
    Return the action string with every boolean action that has a false value turned into the excluded action, and
    the boolean actions with a value that is neither true nor false. The other actions stay exactly as they are.
    """
    bool_actions = BOOL_ACTIONS.get(scope, frozenset())
    parts = []
    unclear = []
    changed = False
    for part in re.split(r'(?<!\\),', action):
        key_value = part.strip().split("=", 1)
        if len(key_value) == 2 and key_value[0] in bool_actions:
            value = key_value[1].strip()
            if value.lower() in FALSE_VALUES:
                # Keep the space after the separating comma
                part = part[:len(part) - len(part.lstrip())] + f"-{key_value[0]}"
                changed = True
            elif value and value not in TRUE_VALUES:
                unclear.append(part.strip())
        parts.append(part)
    return ",".join(parts) if changed else action, unclear


def upgrade():
    session = orm.Session(bind=op.get_bind())
    try:
        for policy in session.scalars(sa.select(Policy).where(Policy.action.like("%=%"))):
            action, unclear = negate_false_bool_actions(policy.scope, policy.action)
            if action != policy.action:
                log.warning(f"Policy '{policy.name}': boolean actions with a false value are now excluded: {action}")
                policy.action = action
            if unclear:
                log.warning(f"Policy '{policy.name}': boolean actions with a value that is neither true nor false "
                            f"are left as they are and act as enabled: {', '.join(unclear)}")
        session.commit()
    except Exception as e:
        session.rollback()
        log.error(f"Failed to exclude the boolean policy actions with a false value: {e!r}")
        raise


def downgrade():
    # The excluded action means the same in every version, so it is kept
    pass
