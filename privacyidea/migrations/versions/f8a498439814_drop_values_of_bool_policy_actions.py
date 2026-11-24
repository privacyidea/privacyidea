"""v3.14.1: Remove the value of boolean policy actions that are stored with a value other than true, and duplicates

The policy matching only checks whether an action is set and ignores its value, so a stored boolean action with a value
like ``policywrite=False`` or ``triggerchallenge=hotp`` is enabled. Saving a policy stores a boolean action with the
value ``false`` or ``0`` as the excluded action, so this migration removes these values from the stored policies and
saving them again keeps the actions enabled. The policies grant the same rights as before. The migration logs every
policy it changes, so that the administrator can check whether an action is meant to be disabled.

Values that enable the action (``true``, ``True``, ``TRUE`` and ``1``) are left as they are.

``disable_client_token_deletion`` is the exception: the server only sends its value to the authenticator app, which
applies it and reads ``false`` and ``0`` (in any case) as disabled. The migration stores it with such a value as the
excluded action ``-disable_client_token_deletion``, so it stays disabled. The server applies the other container client
actions itself, so they stay enabled like the other boolean actions.

Parsing the action string keeps only the last occurrence of an action given more than once, like
``policywrite=hotp, policywrite=false``, so the migration removes the earlier ones and the policy acts as before. An
action and its exclusion, like ``policywrite`` and ``-policywrite``, are different actions and both stay.

The boolean actions are a snapshot of the policy definitions of this version, so the migration does not depend on the
models of a later version. Boolean actions of token types outside privacyIDEA are not included.

The downgrade does not restore the values and the duplicates, the result means the same in every version.

Revision ID: f8a498439814
Revises: 35815effd77c
Create Date: 2026-10-02 15:00:00.000000

"""
import logging
import re

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm

log = logging.getLogger("alembic.env")

revision = 'f8a498439814'
down_revision = '35815effd77c'
branch_labels = None
depends_on = None

TRUE_VALUES = ("1", "True", "true", "TRUE")
# Compared in lower case, like the authenticator app does
FALSE_VALUES = ("false", "0")

# The boolean container actions that only the authenticator app applies, from the value the server sends it
APP_APPLIED_ACTIONS = frozenset({"disable_client_token_deletion"})

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


def drop_duplicate_actions(action: str) -> tuple[str, list[str]]:
    """
    Return the action string without the earlier occurrences of an action given more than once, and the removed parts
    as they were stored. The last occurrence stays, since it is the one parsing the action string keeps.
    """
    parts = re.split(r'(?<!\\),', action)
    keys = [part.strip().split("=", 1)[0] for part in parts]
    kept = []
    dropped = []
    for i, part in enumerate(parts):
        if keys[i] and keys[i] in keys[i + 1:]:
            dropped.append(part.strip())
        else:
            kept.append(part)
    if not dropped:
        return action, dropped
    # The first remaining part loses the space after the separating comma it had
    kept[0] = kept[0].lstrip()
    return ",".join(kept), dropped


def exclude_disabled_app_actions(scope: str, action: str) -> tuple[str, list[str]]:
    """
    Return the action string with every action the authenticator app applies whose value is false replaced by the
    excluded action, like ``-disable_client_token_deletion``, and the replaced actions as they were stored. The other
    actions stay exactly as they are.
    """
    if scope != "container":
        return action, []
    parts = []
    excluded = []
    for part in re.split(r'(?<!\\),', action):
        key_value = part.strip().split("=", 1)
        if (len(key_value) == 2 and key_value[0] in APP_APPLIED_ACTIONS
                and key_value[1].strip().lower() in FALSE_VALUES):
            excluded.append(part.strip())
            # Keep the space after the separating comma
            part = part[:len(part) - len(part.lstrip())] + f"-{key_value[0]}"
        parts.append(part)
    return (",".join(parts) if excluded else action), excluded


def drop_bool_action_values(scope: str, action: str) -> tuple[str, list[str]]:
    """
    Return the action string with the value removed from every boolean action whose value is not true, and the
    removed actions as they were stored. The other actions stay exactly as they are.
    """
    bool_actions = BOOL_ACTIONS.get(scope, frozenset())
    parts = []
    dropped = []
    for part in re.split(r'(?<!\\),', action):
        key_value = part.strip().split("=", 1)
        if len(key_value) == 2 and key_value[0] in bool_actions and key_value[1].strip() not in TRUE_VALUES:
            dropped.append(part.strip())
            # Keep the space after the separating comma
            part = part[:len(part) - len(part.lstrip())] + key_value[0]
        parts.append(part)
    return (",".join(parts) if dropped else action), dropped


def upgrade():
    session = orm.Session(bind=op.get_bind())
    try:
        for policy in session.scalars(sa.select(Policy).where(Policy.action.isnot(None))):
            action, duplicates = drop_duplicate_actions(policy.action)
            if duplicates:
                log.warning(f"Policy '{policy.name}': removed the earlier occurrences of actions given more than once: "
                            f"{', '.join(duplicates)}. The last occurrence, which the policy used, stays.")
            action, excluded = exclude_disabled_app_actions(policy.scope, action)
            if excluded:
                # The policy may contain the excluded action already
                action, _ = drop_duplicate_actions(action)
                log.warning(f"Policy '{policy.name}': stored {', '.join(excluded)} as excluded action, so it stays "
                            f"disabled in the authenticator app.")
            action, dropped = drop_bool_action_values(policy.scope, action)
            if dropped:
                log.warning(f"Policy '{policy.name}': removed the value of the boolean actions {', '.join(dropped)}. "
                            f"They stay enabled as before.")
            if action != policy.action:
                policy.action = action
        session.commit()
    except Exception as e:
        session.rollback()
        log.error(f"Failed to remove the values and duplicates of the policy actions: {e!r}")
        raise


def downgrade():
    # The cleaned action string means the same in every version, so it is kept
    pass
