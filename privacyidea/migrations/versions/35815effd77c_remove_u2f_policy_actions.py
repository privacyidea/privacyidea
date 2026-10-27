"""v3.14: Remove the policy actions of the u2f token type

The u2f token type was removed, so its policy actions ("enrollU2F" and the actions starting with "u2f_") are no
longer valid. A stored policy that still contains one of them fails the validation of every later change and of
every import of an export of it. The actions are removed from the stored policies, the remaining actions keep their
values. Downgrade does not add them back.

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
                  sa.column("action", sa.UnicodeText()))


def _is_u2f_policy_action(part: str) -> bool:
    """
    Whether one comma separated part of a policy action string is an action of the u2f token type, also when it is
    negated with a leading "!" or "-".
    """
    key = part.strip().split("=", 1)[0]
    if key[:1] in ("!", "-"):
        key = key[1:]
    return key == "enrollU2F" or key.startswith("u2f_")


def upgrade() -> None:
    connection = op.get_bind()
    changed = []
    try:
        for policy_id, name, action in connection.execute(sa.select(policy.c.id, policy.c.name,
                                                                    policy.c.action)).all():
            if not action:
                continue
            # The action string is split at the commas that are not escaped, the way the policy engine reads it
            parts = re.split(r"(?<!\\),", action)
            kept = [part.strip() for part in parts if not _is_u2f_policy_action(part)]
            if len(kept) != len(parts):
                connection.execute(policy.update().where(policy.c.id == policy_id).values(action=", ".join(kept)))
                changed.append(name)
    except Exception as exx:
        print(f"Could not remove the policy actions of the u2f token type: {exx}")
        raise
    if changed:
        print(f"Removed the policy actions of the u2f token type from the policies {', '.join(sorted(changed))}.")


def downgrade() -> None:
    pass
