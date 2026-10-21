/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { SchemaPath, pattern, required, validate } from "@angular/forms/signals";
import { reservedNames } from "./reserved-names.utils";

export { reservedNames } from "./reserved-names.utils";

/**
 * Error kinds emitted by the helpers in this file and by the built-in rules of `@angular/forms/signals`.
 * Templates read them through `hasError(field, ERR.required)` so a kind is spelled in one place.
 * `parse` is the kind of a `type="number"` input that holds text the browser cannot turn into a number.
 */
export const ERR = {
  required: "required",
  pattern: "pattern",
  reservedName: "reservedName",
  minLength: "minLength",
  maxLength: "maxLength",
  min: "min",
  max: "max",
  parse: "parse",
  pinMismatch: "pinMismatch",
  nameTaken: "nameTaken"
} as const;

/**
 * Characters allowed in the name of a resolver, server, connector, policy and similar resources.
 * Mirrors `sanity_name_check` in `privacyidea/lib/utils/__init__.py`, which accepts `^[A-Za-z0-9_\-\.]+$`.
 * The `*` lets an empty value through so `required` alone reports it.
 */
export const IDENTIFIER_PATTERN = /^[a-zA-Z0-9._-]*$/;

/** Like {@link IDENTIFIER_PATTERN} and additionally allows the space, which event handler names may contain. */
export const EVENT_NAME_PATTERN = /^[a-zA-Z0-9._ -]*$/;

/**
 * Names a user resolver or machine resolver must not have.
 *
 * The backend does not reject these names itself: `sanity_name_check`
 * (`privacyidea/lib/utils/__init__.py`) only checks the character set, which `.` and `..` satisfy.
 * They are reserved because of how the REST routes overlap:
 * - `test`: `POST /resolver/test` (`test_resolver` in `privacyidea/api/resolver.py`) and
 *   `POST /machineresolver/test` (`privacyidea/api/machineresolver.py`) are the connection-test routes. They win over
 *   the save routes `POST /resolver/<resolver>` and `POST /machineresolver/<resolver>`, so a resolver named `test`
 *   would never be saved.
 * - `.` and `..`: dot segments, which HTTP clients and proxies resolve away before the request reaches the route.
 *
 * Forms of other resources reserve their own names (for example `test_request` or `send_test_email`) and pass them
 * to {@link identifierName} through the `reserved` option.
 */
export const RESOLVER_RESERVED_NAMES = ["test", ".", ".."] as const;

/**
 * Rules for the name of a resource: required, only {@link IDENTIFIER_PATTERN} characters and, when `reserved` is
 * given, none of the reserved names. Emits the kinds `required`, `pattern` and `reservedName`.
 * Event handler names use `EVENT_NAME_PATTERN` and add their own `pattern` rule.
 */
export function identifierName(path: SchemaPath<string>, opts?: { reserved?: readonly string[] }): void {
  required(path);
  pattern(path, IDENTIFIER_PATTERN);
  if (opts?.reserved) {
    reservedNames(path, opts.reserved);
  }
}

/**
 * `required` that also rejects a value made of whitespace only. An empty value yields exactly one `required` error.
 */
export function requiredNonBlank(path: SchemaPath<string>): void {
  required(path);
  validate(path, (ctx) => {
    const value = ctx.value();
    return value !== "" && value.trim() === "" ? [{ kind: ERR.required }] : [];
  });
}

/**
 * Rejects an empty array with a `required` error. The built-in `required` accepts `[]`, so it does not
 * cover multi-select values or lists that must contain at least one entry.
 */
export function requiredNonEmptyArray<T>(path: SchemaPath<T[]>): void {
  validate(path, (ctx) => (ctx.value().length > 0 ? [] : [{ kind: ERR.required }]));
}

/**
 * Rejects a value that differs from the one `other` returns, for example a repeated PIN.
 * `other` is read inside the validator, so the rule re-runs when the other value changes.
 */
export function mustEqual(path: SchemaPath<string>, other: () => string, kind: string = ERR.pinMismatch): void {
  validate(path, (ctx) => (ctx.value() === other() ? [] : [{ kind }]));
}
