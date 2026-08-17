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
import { TestBed } from "@angular/core/testing";
import { TableState } from "@core/models/table_state/table-state";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";

/**
 * Drives a table's TableState through the states its page depends on.
 *
 * The options handed to a TableState are callbacks, so they only run when something asks the state
 * for its status. A table whose spec never does that leaves its read right, its row count and its
 * filter predicate unexecuted - including the name of the right, which is a plain string and is
 * otherwise checked by nothing.
 *
 * Rights are changed through authData rather than by stubbing actionAllowed: the status is a
 * computed, so it only re-evaluates when a signal it read actually changes.
 *
 * @param right the read right this table is gated on, or undefined for a table without one.
 */
export function expectsTableStateGating(args: {
  state: TableState;
  right?: string;
  /** For specs that drive rights through something other than authData, e.g. jwtData. */
  setRights?: (rights: string[]) => void;
}): void {
  const { state, right, setRights } = args;
  const authService = TestBed.inject(AuthService) as unknown as MockAuthService;

  // Some specs pin actionAllowed to a fixed answer, which would ignore the rights set below.
  // Put it back on the rights signal so this check means something wherever it is used.
  if (!setRights && jest.isMockFunction(authService.actionAllowed)) {
    (authService.actionAllowed as jest.Mock).mockImplementation((action: string) =>
      authService.rights().includes(action)
    );
  }

  // No change detection here on purpose: the status is a computed, so it is up to date as soon as
  // the rights signal is set, and running change detection mid-flip trips NG0100 in some templates.
  const withRights =
    setRights ?? ((rights: string[]) => authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights }));

  if (right) {
    withRights([]);
    expect(state.status()).toBe("denied");
    expect(state.showTable()).toBe(false);

    withRights([right]);
    expect(state.status()).not.toBe("denied");
  }

  // Reached only once the right allows it, so these run against the table's own count and filter.
  expect(["loading", "empty", "filtered", "ready", "error"]).toContain(state.status());
  expect(typeof state.canResetFilter).toBe("boolean");

  // The two ways the state panel calls back into the page.
  state.retry();
  if (state.canResetFilter) {
    state.resetFilter();
  }
}
