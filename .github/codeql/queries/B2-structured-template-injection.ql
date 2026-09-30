/**
 * @name User value substituted into a structured string then parsed (SHAPE B2)
 * @description A value is spliced into a string with str.replace() and the result is parsed
 *              with json.loads(). A substituted value containing structural characters can
 *              add or override keys.
 * @kind problem
 * @problem.severity warning
 * @precision medium
 * @id privacyidea/structured-template-injection
 * @tags security
 */

import python

predicate replaceAssign(AssignStmt a, string name) {
  a.getATarget().(Name).getId() = name and
  a.getValue().(Call).getFunc().(Attribute).getName() = "replace"
}

from Call loads, string name, AssignStmt a
where
  loads.getFunc().(Attribute).getName() = "loads" and
  loads.getFunc().(Attribute).getObject().(Name).getId() = "json" and
  loads.getArg(0).(Name).getId() = name and
  replaceAssign(a, name) and
  a.getScope() = loads.getScope()
select loads,
  "json.loads() parses '" + name + "', which is built with str.replace() (SHAPE B2): a substituted value can inject structure."
