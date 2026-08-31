"""
Dev tool: regenerate the multi_device (backup-eligible) passkey fixture block in
tests/passkey_base.py.

The backup-eligible (BE) / backup-state (BS) flags that determine a WebAuthn credential's
device_type live inside the signed region of authenticatorData, so a realistic multi_device
fixture cannot be produced by hand-editing the single_device fixture already in
passkey_base.py without invalidating its signature. This script instead locally simulates a
software authenticator (a fresh ECDSA P-256 keypair, real ECDSA/SHA-256 signing) with full
control over those flag bits, and verifies every response it builds against the real
py_webauthn verification functions before writing anything out - so the fixture is
guaranteed to be genuinely valid, not just plausible-looking.

Not a permanent test dependency: this only needs to run when a fixture is (re)generated.
It writes tests/passkey_base.py in place, so review the diff (and rerun the passkey test
suite) after running it.

Usage: python3 tests/generate_passkey_multi_device_fixture.py
"""
import base64
import hashlib
import json
import os
import struct
from pathlib import Path

import cbor2
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from webauthn import verify_authentication_response, verify_registration_response
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.exceptions import InvalidAuthenticationResponse

RP_ID = "cool.nils"
ORIGIN = "https://cool.nils:5000"
TARGET = Path(__file__).resolve().parent / "passkey_base.py"

UP, UV, BE, BS, AT = 0x01, 0x04, 0x08, 0x10, 0x40


def b64std(data: bytes) -> str:
    return base64.b64encode(data).decode()


def dq(s: str) -> str:
    # These values are base64/base64url text (alnum, +, /, =, -, _ only), never containing a quote or
    # backslash, so a plain manual double-quote wrap is always a valid, faithful Python string literal.
    assert '"' not in s and "\\" not in s
    return f'"{s}"'


def py_assign(name: str, value: str, indent: str = "        ") -> str:
    """Emit `self.<name> = <value>` as valid, verifiable Python source: a single-line assignment when it
    fits within the project's 120-column limit, otherwise an implicitly-concatenated multi-line string
    (continuation lines aligned under the opening paren) built without any manual copy/paste step (so
    there is no way to silently corrupt a byte in the middle of the literal)."""
    prefix = f"{indent}self.{name} = ("
    single = f"{indent}self.{name} = {dq(value)}"
    if len(single) <= 120:
        return single
    chunk_len = 120 - len(prefix) - 2  # closing quote, and the opening quote of each chunk
    chunks = [value[i:i + chunk_len] for i in range(0, len(value), chunk_len)]
    lines = [prefix + dq(chunks[0])]
    for chunk in chunks[1:]:
        lines.append(" " * len(prefix) + dq(chunk))
    lines[-1] += ")"
    assert all(len(line) <= 120 for line in lines), "chunking still exceeds 120 columns"
    return "\n".join(lines)


def build_authdata(rp_id: str, flags: int, sign_count: int, attested: bytes = b"") -> bytes:
    return hashlib.sha256(rp_id.encode()).digest() + bytes([flags]) + struct.pack(">I", sign_count) + attested


def cose_key(public_key: ec.EllipticCurvePublicKey) -> bytes:
    numbers = public_key.public_numbers()
    return cbor2.dumps({
        1: 2,  # kty: EC2
        3: -7,  # alg: ES256
        -1: 1,  # crv: P-256
        -2: numbers.x.to_bytes(32, "big"),
        -3: numbers.y.to_bytes(32, "big"),
    })


def client_data(type_: str, challenge_string: str, origin: str) -> bytes:
    payload = {
        "type": type_,
        "challenge": bytes_to_base64url(challenge_string.encode("utf-8")),
        "origin": origin,
    }
    return json.dumps(payload, separators=(",", ":")).encode()


def sign(private_key: ec.EllipticCurvePrivateKey, message: bytes) -> bytes:
    # ECDSA signatures over P-256/SHA-256, DER-encoded, exactly as a real authenticator produces.
    return private_key.sign(message, ec.ECDSA(hashes.SHA256()))


def main() -> None:
    content = TARGET.read_text()
    if "registration_challenge_multi_device" in content:
        raise SystemExit(
            f"{TARGET} already has a multi_device fixture block. Remove it first if you want to "
            "regenerate it (the fixture values only need to change if the verification logic they "
            "exercise changes)."
        )

    priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    pub = priv.public_key()
    credential_id = os.urandom(32)
    aaguid = b"\x00" * 16

    # ---- Registration: multi_device (backup-eligible AND already backed up) ----
    reg_challenge_str = bytes_to_base64url(os.urandom(32))
    reg_flags = UP | AT | BE | BS
    attested = aaguid + struct.pack(">H", len(credential_id)) + credential_id + cose_key(pub)
    authdata_reg = build_authdata(RP_ID, reg_flags, 0, attested)
    attestation_object = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": authdata_reg})
    client_data_reg = client_data("webauthn.create", reg_challenge_str, ORIGIN)

    reg_result = verify_registration_response(
        credential={
            "id": bytes_to_base64url(credential_id),
            "rawId": bytes_to_base64url(credential_id),
            "response": {
                "attestationObject": b64std(attestation_object),
                "clientDataJSON": b64std(client_data_reg),
            },
            "type": "public-key",
            "authenticatorAttachment": "platform",
        },
        expected_challenge=reg_challenge_str.encode("utf-8"),
        expected_origin=ORIGIN,
        expected_rp_id=RP_ID,
    )
    assert reg_result.credential_device_type == "multi_device", reg_result.credential_device_type
    assert reg_result.credential_backed_up is True
    print("Registration verified as genuine multi_device credential, backed_up=True")

    user_handle = os.urandom(64)

    def build_auth_response(
        sign_count: int, require_uv: bool, credential_current_sign_count: int
    ) -> tuple[str, bytes, bytes, bytes, int]:
        challenge_str = bytes_to_base64url(os.urandom(32))
        flags = UP | BE | BS | (UV if require_uv else 0)
        authdata = build_authdata(RP_ID, flags, sign_count)
        cdata = client_data("webauthn.get", challenge_str, ORIGIN)
        cdata_hash = hashlib.sha256(cdata).digest()
        sig = sign(priv, authdata + cdata_hash)

        result = verify_authentication_response(
            credential={
                "id": bytes_to_base64url(credential_id),
                "rawId": bytes_to_base64url(credential_id),
                "response": {
                    "authenticatorData": b64std(authdata),
                    "clientDataJSON": b64std(cdata),
                    "signature": b64std(sig),
                    "userHandle": b64std(user_handle),
                },
                "type": "public-key",
                "authenticatorAttachment": "platform",
                "clientExtensionResults": {},
            },
            expected_challenge=challenge_str.encode("utf-8"),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            require_user_verification=require_uv,
            credential_current_sign_count=credential_current_sign_count,
            credential_public_key=reg_result.credential_public_key,
        )
        assert result.credential_device_type == "multi_device", result.credential_device_type
        return challenge_str, authdata, cdata, sig, flags

    # Three independent genuine multi_device authentication responses (distinct challenges/sign counts,
    # each consumable exactly once): one for the reject-by-policy test, one for the accept-by-policy test,
    # one to be BE-bit-tampered afterwards for the negative/spoofing test.
    challenge_reject, authdata_reject, cdata_reject, sig_reject, _ = build_auth_response(6, False, 0)
    print("Authentication A (reject-by-policy case) verified as genuine multi_device credential")

    challenge_accept, authdata_accept, cdata_accept, sig_accept, _ = build_auth_response(7, True, 6)
    print("Authentication B (accept-by-policy case) verified as genuine multi_device credential")

    challenge_tamper, authdata_tamper, cdata_tamper, sig_tamper, tamper_flags = build_auth_response(8, True, 7)
    print("Authentication C (tamper case) verified as genuine multi_device credential")

    # ---- Negative/tamper check: flip the BE bit on the *signed* authData, keep the original ----
    # ---- signature (attacker has no private key) -> must be rejected. This is the "can you  ----
    # ---- trick a non-platform assertion into looking like a different device type" question. ----
    tampered_flags = tamper_flags & ~BE  # try to make it look single_device, signature is now stale
    tampered_authdata = build_authdata(RP_ID, tampered_flags, 8)
    try:
        verify_authentication_response(
            credential={
                "id": bytes_to_base64url(credential_id),
                "rawId": bytes_to_base64url(credential_id),
                "response": {
                    "authenticatorData": b64std(tampered_authdata),
                    "clientDataJSON": b64std(cdata_tamper),
                    "signature": b64std(sig_tamper),  # stale signature over the ORIGINAL flags
                    "userHandle": b64std(user_handle),
                },
                "type": "public-key",
                "authenticatorAttachment": "platform",
                "clientExtensionResults": {},
            },
            expected_challenge=challenge_tamper.encode("utf-8"),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            require_user_verification=True,
            credential_current_sign_count=7,
            credential_public_key=reg_result.credential_public_key,
        )
        raise SystemExit("TAMPER CHECK FAILED: verification accepted a flag-tampered signature!")
    except InvalidAuthenticationResponse as ex:
        print(f"Tamper check passed: bit-flipped BE flag correctly rejected ({ex})")

    block_lines = [
        "",
        "        # Multi-device (backup-eligible) registration and authentication data. The backup-eligible flag",
        "        # lives inside the signed region of authenticatorData, so it cannot be produced by editing the",
        "        # single-device fixture above without invalidating its signature - this is a second, independently",
        "        # generated credential (locally simulated ECDSA P-256 authenticator, not real hardware) that is",
        "        # genuinely signed as backup-eligible, verified against the real py_webauthn verification functions",
        "        # at generation time.",
        py_assign("registration_challenge_multi_device", reg_challenge_str),
        py_assign("registration_attestation_multi_device", b64std(attestation_object)),
        py_assign("registration_client_data_multi_device", b64std(client_data_reg)),
        py_assign("credential_id_multi_device", bytes_to_base64url(credential_id)),
        py_assign("authenticator_attachment_multi_device", "platform"),
        py_assign("user_handle_multi_device", b64std(user_handle)),
        "",
        "        # Reject case: used with a SCOPE.AUTH policy restricting to single_device, must be denied",
        py_assign("authentication_challenge_multi_device_reject", challenge_reject),
        py_assign("authenticator_data_multi_device_reject", b64std(authdata_reject)),
        py_assign("authentication_client_data_multi_device_reject", b64std(cdata_reject)),
        py_assign("authentication_signature_multi_device_reject", b64std(sig_reject)),
        "        self.authentication_response_multi_device_reject = {",
        '            "clientDataJSON": self.authentication_client_data_multi_device_reject,',
        '            "authenticatorData": self.authenticator_data_multi_device_reject,',
        '            "signature": self.authentication_signature_multi_device_reject,',
        '            "userHandle": self.user_handle_multi_device,',
        '            "credential_id": self.credential_id_multi_device,',
        "        }",
        "",
        "        # Accept case: used with a SCOPE.AUTH policy restricting to multi_device, must succeed",
        py_assign("authentication_challenge_multi_device_accept", challenge_accept),
        py_assign("authenticator_data_multi_device_accept", b64std(authdata_accept)),
        py_assign("authentication_client_data_multi_device_accept", b64std(cdata_accept)),
        py_assign("authentication_signature_multi_device_accept", b64std(sig_accept)),
        "        self.authentication_response_multi_device_accept = {",
        '            "clientDataJSON": self.authentication_client_data_multi_device_accept,',
        '            "authenticatorData": self.authenticator_data_multi_device_accept,',
        '            "signature": self.authentication_signature_multi_device_accept,',
        '            "userHandle": self.user_handle_multi_device,',
        '            "credential_id": self.credential_id_multi_device,',
        "        }",
        "",
        "        # Tamper case: a genuine multi_device response with the backup-eligible bit flipped off in",
        "        # authenticatorData while keeping the ORIGINAL signature (an attacker forging this has no private",
        "        # key), used to prove the device type cannot be spoofed by editing the wire data post-signature.",
        py_assign("authentication_challenge_multi_device_tamper", challenge_tamper),
        py_assign("authentication_client_data_multi_device_tamper", b64std(cdata_tamper)),
        py_assign("authentication_signature_multi_device_tamper", b64std(sig_tamper)),
        py_assign("authenticator_data_multi_device_tamper_be_flipped", b64std(tampered_authdata)),
        "        self.authentication_response_multi_device_tamper = {",
        '            "clientDataJSON": self.authentication_client_data_multi_device_tamper,',
        '            "authenticatorData": self.authenticator_data_multi_device_tamper_be_flipped,',
        '            "signature": self.authentication_signature_multi_device_tamper,',
        '            "userHandle": self.user_handle_multi_device,',
        '            "credential_id": self.credential_id_multi_device,',
        "        }",
    ]
    block = "\n".join(block_lines) + "\n"

    anchor = (
        "        self.authentication_response_uv = {\n"
        '            "clientDataJSON": self.authentication_client_data_uv,\n'
        '            "authenticatorData": self.authenticator_data_uv,\n'
        '            "signature": self.authentication_signature_uv,\n'
        '            "userHandle": self.user_handle,\n'
        '            "credential_id": self.credential_id,\n'
        "        }\n"
    )
    if content.count(anchor) != 1:
        raise SystemExit(f"Anchor block not found exactly once in {TARGET}, refusing to write.")
    TARGET.write_text(content.replace(anchor, anchor + block))
    print(f"Wrote fixture block into {TARGET}")


if __name__ == "__main__":
    main()
