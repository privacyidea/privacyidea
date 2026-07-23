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
import { inject } from "@angular/core";
import { RedirectFunction } from "@angular/router";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { PolicyAction } from "@services/auth/policy-actions";

/**
 * Build a route redirect that resolves to the first candidate path whose policy action the user is allowed, in the
 * given order, falling back to *fallback* when none is allowed. Use for a parent route whose default child differs
 * per the user's rights -- add new section landing redirects to this file.
 */
export function firstAllowedRedirect(
  candidates: readonly [action: PolicyAction, path: string][],
  fallback: string
): RedirectFunction {
  return (): string => {
    const authService: AuthServiceInterface = inject(AuthService);
    const match = candidates.find(([action]) => authService.actionAllowed(action));
    return match ? match[1] : fallback;
  };
}

/**
 * Redirect target for the `/logs` parent route: the first sub-tab the user is allowed to see, in display order
 * (audit log -> authentication log -> known clients). Falls back to "audit" when none is allowed -- the Logs menu is
 * hidden in that case, so this only guards direct navigation.
 */
export const logsLandingRedirect: RedirectFunction = firstAllowedRedirect(
  [
    ["auditlog", "audit"],
    ["authentication_log_read", "authentication-log"],
    ["clienttype", "clients"],
    ["user_lockout_read", "locked-users"]
  ],
  "audit"
);
