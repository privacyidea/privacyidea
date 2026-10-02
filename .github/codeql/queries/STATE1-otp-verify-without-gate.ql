/**
 * @name Token OTP verified without the usability gate (STATE)
 * @description A call to `token.check_otp()` in the orchestration layer whose enclosing function
 *              does not also run the composed usability gate (check_all / check_token_list). The
 *              standard path gates every candidate with check_all; a verify that skips it can
 *              accept a disabled, revoked, expired or not-yet-enrolled token.
 * @kind problem
 * @problem.severity warning
 * @precision medium
 * @id privacyidea/otp-verify-without-gate
 * @tags security
 */

import python

/** `scope` contains a direct call to a function/method named `name`. */
predicate callsName(Scope scope, string name) {
  exists(Call c | c.getScope() = scope and c.getFunc().(Attribute).getName() = name)
  or
  exists(Call c | c.getScope() = scope and c.getFunc().(Name).getId() = name)
}

from Call verify, Function f
where
  verify.getFunc().(Attribute).getName() = "check_otp" and
  f = verify.getScope() and
  // Orchestration layer only - exclude the token-class definitions and their internal use,
  // where check_otp is implemented and composed by the token's own check()/check_all.
  not f.getLocation().getFile().getRelativePath().matches("privacyidea/lib/tokens/%") and
  not f.getLocation().getFile().getRelativePath().matches("%tokenclass.py") and
  // The enclosing function does not itself run the composed gate.
  not callsName(f, "check_all") and
  not callsName(f, "check_token_list")
select verify,
  "token.check_otp() is reached in '" + f.getName() +
  "' without check_all / check_token_list in the same function (STATE: the composed usability gate is not applied here)."
