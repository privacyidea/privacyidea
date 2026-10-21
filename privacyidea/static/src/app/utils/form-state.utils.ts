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

import { FieldState, FieldTree, submit } from "@angular/forms/signals";

/**
 * True when `field` currently has an error of the given kind. Works for every field type
 * (string, boolean, `number | null`, `string[]`, a key of a `Record` model).
 * A `mat-error` inside a `mat-form-field` renders only once the bound field is touched, so templates that wrap this
 * in `@if` there need no extra `touched()` check. Error text outside a `mat-form-field` (for example next to a
 * `mat-checkbox`) needs `field().touched()` in its own condition.
 */
export function hasError(field: FieldTree<unknown>, kind: string): boolean {
  return field()
    .errors()
    .some((error) => error.kind === kind);
}

/**
 * Sets the value of a field the way a bound control does: through `controlValue`, which marks the field dirty.
 * A programmatic `model.update(...)` never marks a field dirty, so clear buttons call this instead.
 * `FieldTree<T>` is a conditional type, so the state is cast to `FieldState<T>` to write a generic `T`.
 */
export function clearField<T>(field: FieldTree<T>, empty: T): void {
  (field() as FieldState<T>).controlValue.set(empty);
}

/**
 * Marks `form` and every non-disabled descendant touched, so each `mat-error` renders.
 * `markAsTouched()` on the root only touches the root. The recursive marking is internal to `submit()`, which is
 * called here with an empty action. The action runs only when the form is valid, so the result tells whether
 * the form has no blocking errors (a pending async validator does not block). Touching happens synchronously,
 * before the returned promise settles. A call made while a previous call on the same form is still running
 * returns `false`; the fields are already touched by then.
 */
export function touchAll(form: FieldTree<unknown>): Promise<boolean> {
  return submit(form, { action: async () => undefined });
}
