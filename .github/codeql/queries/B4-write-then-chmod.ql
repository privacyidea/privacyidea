/**
 * @name Secret file written before its mode is restricted (SHAPE B4)
 * @description A file opened for writing with the builtin open() and then chmod'd to an
 *              owner-only mode afterwards is world-readable in the window between the two.
 * @kind problem
 * @problem.severity warning
 * @precision medium
 * @id privacyidea/write-then-chmod
 * @tags security
 */

import python

/** builtin `open(path, "..w..")` — a write that cannot set a restrictive mode. */
predicate writeOpen(Call c, string pathName) {
  c.getFunc().(Name).getId() = "open" and
  c.getArg(0).(Name).getId() = pathName and
  exists(StringLiteral m | m = c.getArg(1) | m.getText().matches("%w%"))
}

/** an owner-only chmod: `path.chmod(0o400/0o600/...)` or `os.chmod(path, 0o...)`. */
predicate ownerOnlyChmod(Call c, string pathName, int mode) {
  exists(Attribute a | a = c.getFunc() and a.getName() = "chmod" |
    a.getObject().(Name).getId() = pathName and c.getArg(0).(IntegerLiteral).getValue() = mode
    or
    a.getObject().(Name).getId() = "os" and c.getArg(0).(Name).getId() = pathName and
    c.getArg(1).(IntegerLiteral).getValue() = mode
  ) and
  mode = [256, 288, 320, 384, 448] // 0o400 0o440 0o500 0o600 0o700
}

from Call openCall, Call chmodCall, string pathName, int mode
where
  writeOpen(openCall, pathName) and
  ownerOnlyChmod(chmodCall, pathName, mode) and
  openCall.getScope() = chmodCall.getScope()
select chmodCall,
  "'" + pathName + "' is opened for writing then chmod'd to 0o" + mode.toString() +
  " afterwards (SHAPE B4): the mode is set after creation, so the file is world-readable in between."
