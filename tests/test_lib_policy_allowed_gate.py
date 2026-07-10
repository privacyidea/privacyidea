# SPDX-FileCopyrightText: 2026 Nils Behlen <nils.behlen@netknights.it>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression guard for the ``Match.allowed()`` vs. ``Match.enforced()`` distinction.

``Match.allowed()`` is fail-open: it returns True when the whole policy scope is
unconfigured. That is correct for a *permission gate* (``if not match.allowed():
raise PolicyError(...)``), but wrong for an *opt-in enforcement toggle*, where a
missing policy would enable the feature by default. Toggles must use
``Match.enforced()`` / ``Match.any()`` instead.

This test statically inspects the pre-/postpolicy modules and fails if a value
captured from ``.allowed()`` is not consumed by a negated-and-raising guard in
the same function. New enforcement toggles that misuse ``.allowed()`` therefore
break CI instead of shipping silently. See issue #5570.

A rare, deliberate fail-open permission check that is used positively rather than
as a raising gate (e.g. "does this admin effectively have the right?") can opt out
by adding a trailing ``# allowed-permission-check`` marker comment on the call.
"""
import ast
from pathlib import Path

import privacyidea

MODULES = ["api/lib/prepolicy.py", "api/lib/postpolicy.py"]

# Trailing marker that opts a deliberate fail-open permission check out of the gate rule.
OPT_OUT_MARKER = "allowed-permission-check"

PACKAGE_ROOT = Path(privacyidea.__file__).resolve().parent


def _is_allowed_call(node):
    """True if the node is a call to an attribute named ``allowed`` (i.e. ``....allowed(...)``)."""
    return (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "allowed")


def _guards_and_raises(function_node, variable_name):
    """
    True if ``function_node`` contains an ``if`` statement that tests ``not <variable_name>``
    and raises inside its body. This is the permission-gate pattern for which the fail-open
    ``allowed()`` semantics are intended.
    """
    for node in ast.walk(function_node):
        if not isinstance(node, ast.If):
            continue
        # The variable must appear in a boolean-negated position within the test, e.g. `if not x`.
        negates_variable = any(
            isinstance(sub, ast.UnaryOp) and isinstance(sub.op, ast.Not)
            and isinstance(sub.operand, ast.Name) and sub.operand.id == variable_name
            for sub in ast.walk(node.test))
        if not negates_variable:
            continue
        if any(isinstance(sub, ast.Raise) for sub in ast.walk(node)):
            return True
    return False


def _collect_violations(source_path):
    """Return a list of (lineno, variable_name) for ungated ``.allowed()`` assignments."""
    source = source_path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    tree = ast.parse(source, filename=str(source_path))
    violations = []
    for function_node in ast.walk(tree):
        if not isinstance(function_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(function_node):
            if not isinstance(node, ast.Assign) or not _is_allowed_call(node.value):
                continue
            # Allow a deliberate fail-open permission check to opt out via a marker comment
            # anywhere within the physical lines of the assignment statement.
            statement_source = "\n".join(source_lines[node.lineno - 1:node.end_lineno])
            if OPT_OUT_MARKER in statement_source:
                continue
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                if not _guards_and_raises(function_node, target.id):
                    violations.append((node.lineno, target.id))
    return violations


def test_allowed_results_are_only_used_as_permission_gates():
    all_violations = []
    for relative in MODULES:
        source_path = PACKAGE_ROOT / relative
        for lineno, variable_name in _collect_violations(source_path):
            all_violations.append(f"{relative}:{lineno}: `{variable_name} = ....allowed()` "
                                  f"is not consumed by an `if not {variable_name}: ... raise` gate")

    assert not all_violations, (
        "Match.allowed() is fail-open and must only be used as a permission gate.\n"
        "For an opt-in enforcement/feature toggle use Match.enforced()/Match.any() instead.\n"
        "Offending sites:\n  " + "\n  ".join(all_violations))
