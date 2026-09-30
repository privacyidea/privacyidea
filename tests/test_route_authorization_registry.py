"""
Authorization guardrail for the API routes.

Every route in ``privacyidea/api/`` must carry an authorization decorator
(``prepolicy`` / ``admin_required`` / ``user_required`` / ``admin_or_user_required`` /
``login_required`` / ``check_auth_token``). A route without one, and not listed in the
``BASELINE`` below, fails this test - so a new endpoint cannot ship without an
authorization gate being a conscious, reviewed decision.

The baseline holds the routes that are ungated on purpose or gate elsewhere:
  * PUBLIC       - anonymous by design (the ``/validate`` flow, the token-type endpoint,
                   the registration status, health probes).
  * GATED-ELSEWHERE - authorization happens in a ``before_request`` handler or inside the
                   view body (e.g. ``check_auth_token`` in the health check), not as a decorator.
  * SELF         - keyed to the logged-in identity from the JWT.
  * KNOWN-GAP    - a gap recorded by the security review; remove the entry once it is fixed.

This is the counterpart to the CodeQL ``route-missing-authz`` query: static analysis can flag a
value read from the wrong source, but not the *absence* of a check, which is what this asserts.
"""
import ast
import glob
import os

API_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "privacyidea", "api")

AUTHZ_DECORATORS = {
    "prepolicy",
    "admin_required",
    "user_required",
    "admin_or_user_required",
    "login_required",
    "check_auth_token",
}

# module.function -> reason. Keep the reason short; category prefix as described above.
BASELINE = {
    "application.get_applications": "GATED-ELSEWHERE: static application-type list",
    "container.get_types": "GATED-ELSEWHERE: static container-type list",
    "container.get_state_types": "GATED-ELSEWHERE: static state-type list",
    "container.get_template_token_types": "GATED-ELSEWHERE: static template-type list",
    "container.create_challenge": "GATED-ELSEWHERE: container registration challenge",
    "healthcheck.healthz": "PUBLIC: health probe",
    "healthcheck.startupz": "PUBLIC: startup probe",
    "healthcheck.livez": "PUBLIC: liveness probe",
    "healthcheck.readyz": "PUBLIC: readiness probe",
    "healthcheck.resolversz": "GATED-ELSEWHERE: check_auth_token(admin) in the body",
    "realm.get_realms_api": "GATED-ELSEWHERE: reduce_realms scoping + before_request",
    "realm.get_super_user_realms": "GATED-ELSEWHERE: config value",
    "realm.get_default_realm_api": "GATED-ELSEWHERE: default realm name",
    "register.register_status": "PUBLIC: self-registration flow",
    "resolver.get_default_resolver_config": "GATED-ELSEWHERE: static resolver defaults",
    "system.get_gpg_keys": "PUBLIC: public GPG keys used for token-import encryption",
    "ttype.token": "PUBLIC: anonymous token-type endpoint (e.g. push polling)",
    "user.get_user_settings_api": "SELF: /user/settings keyed by the JWT identity",
    "user.set_user_settings_api": "SELF: /user/settings keyed by the JWT identity",
    "user.delete_user_settings_api": "SELF: /user/settings keyed by the JWT identity",
    "validate.offlinerefill": "PUBLIC: anonymous /validate endpoint",
    "validate.get_capabilities": "PUBLIC: anonymous /validate endpoint",
    "validate.check_remember_device": "PUBLIC: anonymous /validate endpoint",
    # KNOWN GAPS - recorded by the security review; remove once gated.
    "machineresolver.test_resolver": "KNOWN-GAP: /machineresolver/test has no gate",
    "user.get_user_attribute": "KNOWN-GAP: GET /user/attribute has no gate",
    "user.get_editable_attributes": "KNOWN-GAP: GET /user/editable_attributes has no gate",
}


def _decorator_name(dec: ast.expr) -> str | None:
    node = dec.func if isinstance(dec, ast.Call) else dec
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _ungated_routes() -> set[str]:
    """Return the set of 'module.function' route handlers that have no authorization decorator."""
    ungated = set()
    for path in sorted(glob.glob(os.path.join(API_DIR, "*.py"))):
        module = os.path.basename(path)[:-3]
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            names = {_decorator_name(dec) for dec in node.decorator_list}
            if "route" not in names:
                continue
            if not (names & AUTHZ_DECORATORS):
                ungated.add(f"{module}.{node.name}")
    return ungated


def test_no_ungated_route_outside_baseline():
    new = sorted(_ungated_routes() - set(BASELINE))
    assert not new, (
        "API route(s) without an authorization decorator and not in the baseline: "
        + ", ".join(new)
        + ". Add a @prepolicy/@admin_required/... gate, or - if the route is intentionally "
        "public - add it to BASELINE in this file with a reason."
    )


def test_baseline_has_no_stale_entries():
    stale = sorted(set(BASELINE) - _ungated_routes())
    assert not stale, (
        "BASELINE entries that are now gated or removed - delete them from this file: "
        + ", ".join(stale)
    )
