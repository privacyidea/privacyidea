/**
 * @name Python config executed as code (SHAPE B5)
 * @description Config.from_pyfile / exec run a file's contents as Python. Review whether the
 *              bytes can originate from an archive or another untrusted source (e.g. a restored
 *              backup) rather than a trusted configuration path.
 * @kind problem
 * @problem.severity warning
 * @precision medium
 * @id privacyidea/config-exec-sink
 * @tags security
 */

import python

from Call c, string what
where
  (c.getFunc().(Attribute).getName() = "from_pyfile" and what = "Config.from_pyfile()")
  or
  (c.getFunc().(Name).getId() = "exec" and what = "exec()")
select c,
  what + " runs a file as Python code (SHAPE B5): verify the bytes cannot come from an archive or other untrusted source."
