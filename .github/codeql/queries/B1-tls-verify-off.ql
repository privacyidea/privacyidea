/**
 * @name TLS verification disabled on a secrets path (SHAPE B1)
 * @description An SMTP/TLS or requests client created without certificate
 *              verification, on a path that carries credentials or one-time
 *              passwords. The connection is not authenticated against the
 *              presented certificate.
 * @kind problem
 * @problem.severity warning
 * @precision medium
 * @id privacyidea/tls-verify-off
 * @tags security
 */

import python

/** The value passed for keyword argument `name` in `call`, if any. */
Expr keywordValue(Call call, string name) {
  exists(Keyword k | k = call.getAKeyword() and k.getArg() = name and result = k.getValue())
}

/** A call `smtplib.SMTP_SSL(...)` or `<smtp>.starttls(...)` with no `context=` argument. */
predicate smtpNoContext(Call call, string what) {
  exists(Attribute a | a = call.getFunc() |
    a.getName() = "SMTP_SSL" and what = "smtplib.SMTP_SSL without context="
    or
    a.getName() = "starttls" and what = "SMTP.starttls() without context="
  ) and
  not exists(keywordValue(call, "context"))
}

/** A `requests.<verb>(..., verify=False)` call. */
predicate requestsVerifyFalse(Call call, string what) {
  exists(Attribute a | a = call.getFunc() |
    a.getName() in ["get", "post", "put", "delete", "patch", "head", "request", "options"]
  ) and
  keywordValue(call, "verify").(ImmutableLiteral).booleanValue() = false and
  what = "requests." + call.getFunc().(Attribute).getName() + "(verify=False)"
}

from Call call, string what
where smtpNoContext(call, what) or requestsVerifyFalse(call, what)
select call, "TLS verification is not enforced here: " + what + " (SHAPE B1)."
