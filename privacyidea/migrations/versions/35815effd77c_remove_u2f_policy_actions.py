"""v3.14: Remove the policy actions of the u2f token type

The u2f token type was removed, so its policy actions ("enrollU2F" and the actions starting with "u2f_") are no
longer valid. A stored policy that still contains one of them fails the validation of every later change and of
every import of an export of it. The actions are removed from the stored policies, the remaining actions keep their
values.

A policy whose actions are all u2f actions is deleted with its conditions and its description, because a policy
without actions applies to every action of its scope. In the admin and the user scope, every action is allowed if the
scope has no active policy. So an active policy of these scopes is kept if no other active policy of its scope
remains. It allows nothing in this version, and the migration names it in a warning.

Downgrade does not add the actions back and does not restore the deleted policies.

Revision ID: 35815effd77c
Revises: ad07c259b5c1
Create Date: 2026-10-06 18:00:00.000000

"""
import re

import sqlalchemy as sa
from alembic import op

revision = '35815effd77c'
down_revision = 'ad07c259b5c1'
branch_labels = None
depends_on = None

policy = sa.table("policy", sa.column("id", sa.Integer()), sa.column("name", sa.Unicode(64)),
                  sa.column("scope", sa.Unicode(32)), sa.column("active", sa.Boolean()),
                  sa.column("action", sa.UnicodeText()))
policy_condition = sa.table("policycondition", sa.column("policy_id", sa.Integer()))
policy_description = sa.table("description", sa.column("object_id", sa.Integer()))

# In these scopes every action is allowed if the scope has no active policy
SCOPES_OPEN_WITHOUT_ACTIVE_POLICY = ("admin", "user")


def _is_u2f_policy_action(part: str) -> bool:
    """
    Whether one comma separated part of a policy action string is an action of the u2f token type, also when it is
    negated with a leading "!" or "-".
    """
    key = part.strip().split("=", 1)[0]
    if key[:1] in ("!", "-"):
        key = key[1:]
    return key == "enrollU2F" or key.startswith("u2f_")


def _delete_policy(connection: sa.Connection, policy_id: int) -> None:
    """
    Delete a policy with the rows that refer to it. The foreign keys of the conditions and of the description do not
    cascade, so these rows are deleted first.
    """
    connection.execute(policy_condition.delete().where(policy_condition.c.policy_id == policy_id))
    connection.execute(policy_description.delete().where(policy_description.c.object_id == policy_id))
    connection.execute(policy.delete().where(policy.c.id == policy_id))


def upgrade() -> None:
    connection = op.get_bind()
    changed_names = []
    deleted_names = []
    kept_names = []
    only_u2f_policies = []
    scopes_with_remaining_active_policy = set()
    try:
        for policy_id, name, scope, active, action in connection.execute(
                sa.select(policy.c.id, policy.c.name, policy.c.scope, policy.c.active, policy.c.action)).all():
            # The action string is split at the commas that are not escaped, the way the policy engine reads it
            parts = re.split(r"(?<!\\),", action) if action else []
            if any(_is_u2f_policy_action(part) for part in parts):
                kept_parts = [part.strip() for part in parts if part.strip() and not _is_u2f_policy_action(part)]
                if not kept_parts:
                    only_u2f_policies.append((policy_id, name, scope, bool(active)))
                    continue
                connection.execute(policy.update().where(policy.c.id == policy_id).values(action=", ".join(kept_parts)))
                changed_names.append(name)
            if active:
                scopes_with_remaining_active_policy.add(scope)

        for policy_id, name, scope, active in only_u2f_policies:
            keeps_the_scope_restricted = (active and scope in SCOPES_OPEN_WITHOUT_ACTIVE_POLICY
                                          and scope not in scopes_with_remaining_active_policy)
            if keeps_the_scope_restricted:
                kept_names.append(name)
            else:
                _delete_policy(connection, policy_id)
                deleted_names.append(name)
    except Exception as exx:
        print(f"Could not remove the policy actions of the u2f token type: {exx}")
        raise
    if changed_names:
        print(f"Removed the policy actions of the u2f token type from the policies {', '.join(sorted(changed_names))}.")
    if deleted_names:
        print(f"Deleted the policies {', '.join(sorted(deleted_names))}. They only held policy actions of the u2f "
              "token type.")
    if kept_names:
        print(f"WARNING: The policies {', '.join(sorted(kept_names))} only hold policy actions of the u2f token type "
              "and allow nothing. They are kept, because they are the last active policies of their scope. Without an "
              "active policy in the admin or user scope, every administrator or user gets all rights of that scope. "
              "Replace their actions with other actions. A policy without actions allows every action of its scope. "
              "To delete them, first add another active policy to their scope.")


def downgrade() -> None:
    pass
