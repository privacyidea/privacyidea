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

import { SchemaPath, validate } from "@angular/forms/signals";
import { PolicyActionDetail, PolicyServiceInterface } from "@services/policies/policies.service";

/** Kind of the error reported for a value that `PolicyService.actionValueIsValid` rejects. */
export const INVALID_ACTION_VALUE = "invalidValue";

/**
 * Rule for the value of a policy action: it must be acceptable for the action's type, which
 * `PolicyService.actionValueIsValid` decides. A missing `detail` rejects every value. `detail` is read inside the
 * validator, so the rule re-runs when the action changes.
 */
export function actionValueRule<T extends string | number | boolean>(
  path: SchemaPath<T>,
  policyService: Pick<PolicyServiceInterface, "actionValueIsValid">,
  detail: () => PolicyActionDetail | null | undefined
): void {
  validate(path, (ctx) => {
    const actionDetail = detail();
    return actionDetail && policyService.actionValueIsValid(actionDetail, ctx.value())
      ? []
      : [{ kind: INVALID_ACTION_VALUE }];
  });
}
