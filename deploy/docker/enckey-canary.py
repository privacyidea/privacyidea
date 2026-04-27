"""
enckey canary: verifies the encryption key hasn't been silently swapped.

At pi-init time, we encrypt a known plaintext with the current enckey (via
privacyidea.lib.crypto.encryptPassword, the same primitive PI uses for
sensitive config) and store the ciphertext in the pi_config table under a
reserved key. Every pi worker verifies the canary on startup — if decryption
doesn't return the expected plaintext, the enckey on disk does not match
the one the database was built with, and the container refuses to start.

Subcommands:
    install   Write the canary row (idempotent — skip if already present).
    verify    Read the canary and check it decrypts to the expected value.

Exit codes:
    0   success
    1   canary missing on verify (treated as a soft failure so legacy
        deployments without a canary still start; logs a warning)
    2   canary present but decrypt mismatch — loud failure, bad enckey

Called by entrypoint.sh. Not intended to be used directly.
"""
import sys

from privacyidea.app import create_app
from privacyidea.lib.crypto import FAILED_TO_DECRYPT_PASSWORD, decryptPassword, encryptPassword
from privacyidea.lib.error import HSMException
from privacyidea.models import Config, db

CANARY_KEY = "__enckey_canary_v1"
CANARY_PLAINTEXT = "PRIVACYIDEA_ENCKEY_CANARY_V1"


def install() -> int:
    with create_app("docker", silent=True).app_context():
        existing = Config.query.filter_by(Key=CANARY_KEY).first()
        if existing is not None:
            print(f"[enckey-canary] canary already present at pi_config['{CANARY_KEY}']")
            return 0
        ciphertext = encryptPassword(CANARY_PLAINTEXT)
        row = Config(Key=CANARY_KEY, Value=ciphertext, Type="", Description="enckey canary")
        db.session.add(row)
        db.session.commit()
        print(f"[enckey-canary] installed at pi_config['{CANARY_KEY}']")
        return 0


def verify() -> int:
    with create_app("docker", silent=True).app_context():
        row = Config.query.filter_by(Key=CANARY_KEY).first()
        if row is None:
            print(f"[enckey-canary] WARNING: no canary at pi_config['{CANARY_KEY}']. "
                  "Legacy deployment? Run 'enckey-canary install' via pi-init.",
                  file=sys.stderr)
            return 1
        try:
            decrypted = decryptPassword(row.Value)
        except HSMException as e:
            # HSM (encryption module) could not initialize — enckey is unusable.
            # Indistinguishable from "wrong enckey" as a failure mode, treat as fatal.
            print(f"[enckey-canary] FATAL: HSM initialization failed ({e}). "
                  "The enckey on disk is unusable.", file=sys.stderr)
            return 2
        if decrypted == FAILED_TO_DECRYPT_PASSWORD:
            print(f"[enckey-canary] FATAL: canary decryption failed. The enckey on "
                  f"disk cannot decrypt data encrypted at init time. Do NOT continue "
                  f"— restore the original enckey from backup.", file=sys.stderr)
            return 2
        if decrypted != CANARY_PLAINTEXT:
            print(f"[enckey-canary] FATAL: canary decrypted to unexpected value. "
                  f"The enckey is wrong for this database.", file=sys.stderr)
            return 2
        print("[enckey-canary] OK — enckey matches the database")
        return 0


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("install", "verify"):
        print(f"usage: {sys.argv[0]} (install|verify)", file=sys.stderr)
        return 2
    return {"install": install, "verify": verify}[sys.argv[1]]()


if __name__ == "__main__":
    sys.exit(main())
