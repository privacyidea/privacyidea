/**
 * @name TLS/verification flag defaults to off (FAIL-6)
 * @description A certificate/TLS verification flag read from config with a default of False, so a
 *              configuration that omits the key runs without certificate verification. Distinct from B1, which
 *              catches a literal verify=False / context-less SMTP.
 * @kind problem
 * @problem.severity warning
 * @precision medium
 * @id privacyidea/verify-default-off
 * @tags security
 */

import python

predicate verifyKey(string k) {
  k =
    [
      "tls_verify", "verify_ssl", "ssl_verify", "check_ssl", "verify_tls",
      "verify_certificate", "verify_server_certificate", "verify_ssl_certificate", "verifyssl"
    ]
}

from Call get, StringLiteral key
where
  get.getFunc().(Attribute).getName() = "get" and
  key = get.getArg(0) and
  verifyKey(key.getText().toLowerCase()) and
  get.getArg(1).(ImmutableLiteral).booleanValue() = false
select get,
  "Verification flag '" + key.getText() +
  "' is read with a default of False (FAIL-6): a config that omits the key runs unverified."
