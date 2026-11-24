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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { TableAction } from "@components/shared/table-actions/table-actions.component";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";

/**
 * The toolbar actions a table page hands to its app-table-actions bar.
 *
 * The page keeps them in a protected member, so the component is reached through a structural cast
 * rather than through its own type.
 */
export function toolbarActions(component: object): TableAction[] {
  return (component as unknown as { toolbarActions: () => TableAction[] }).toolbarActions();
}

/**
 * One toolbar action of a table page, found by its id.
 *
 * Throws when the page has no such action, so a misspelled id fails here rather than as a
 * property read on undefined further down the test.
 */
export function toolbarAction(component: object, id: string): TableAction {
  const found = toolbarActions(component).find((candidate) => candidate.id === id);
  if (!found) {
    throw new Error(`no toolbar action ${id}`);
  }
  return found;
}

/**
 * The button the app-table-actions bar draws for an action, found by its visible label.
 *
 * Returns undefined while the bar draws no such button, e.g. while the action is hidden.
 */
export function toolbarButton(fixture: ComponentFixture<unknown>, label: string): HTMLButtonElement | undefined {
  return Array.from<HTMLButtonElement>(fixture.nativeElement.querySelectorAll("app-table-actions button")).find(
    (button) => button.textContent?.includes(label)
  );
}

/**
 * The button the app-table-actions bar draws that matches a CSS selector suffix, such as
 * ".action-button-delete-secondary". The caller expects the button to exist, so the result is typed
 * as the button rather than as nullable.
 */
export function toolbarButtonBySelector(fixture: ComponentFixture<unknown>, selector: string): HTMLButtonElement {
  return fixture.nativeElement.querySelector(`app-table-actions button${selector}`);
}

/**
 * Replaces the rights of the mocked AuthService, leaving the fixture untouched.
 *
 * Rights go through authData rather than a stubbed actionAllowed, so everything computed from them
 * re-evaluates. Use this where the test reads the component directly or re-renders on its own.
 */
export function grantRights(rights: string[]): void {
  const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
  authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights });
}

/**
 * Replaces the rights of the mocked AuthService and renders the fixture, so the toolbar buttons
 * reflect them.
 */
export function setRights(fixture: ComponentFixture<unknown>, rights: string[]): void {
  grantRights(rights);
  fixture.detectChanges();
}
