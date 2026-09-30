/**
 * @name Subprocess argument built by string concatenation (SHAPE B3)
 * @description A subprocess argv element is a path/value built with string concatenation, with
 *              no containment check or a "--" separator. A traversal in the config value or an
 *              option-like user value can escape the intended program/arguments.
 * @kind problem
 * @problem.severity warning
 * @precision low
 * @id privacyidea/subprocess-argv-concat
 * @tags security
 */

import python

predicate isConcat(Expr e) {
  e instanceof BinaryExpr and e.(BinaryExpr).getOp() instanceof Add
}

/** name assigned from a string concatenation in scope s */
predicate concatVar(Scope s, string name) {
  exists(AssignStmt a | a.getScope() = s and a.getATarget().(Name).getId() = name and isConcat(a.getValue()))
}

/** the argv list of a subprocess call, resolved through at most one local variable */
List subprocessArgv(Call c) {
  c.getFunc().(Attribute).getName() = ["Popen", "run", "call", "check_call", "check_output"] and
  (
    result = c.getArg(0)
    or
    exists(AssignStmt a |
      a.getScope() = c.getScope() and
      a.getATarget().(Name).getId() = c.getArg(0).(Name).getId() and
      result = a.getValue()
    )
  )
}

from Call c, Expr elem0
where
  elem0 = subprocessArgv(c).getAnElt() and
  (isConcat(elem0) or concatVar(c.getScope(), elem0.(Name).getId()))
select c,
  "A subprocess argv element is built by string concatenation (SHAPE B3): no path containment / '--' separator."
