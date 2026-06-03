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
import { MatDialog } from "@angular/material/dialog";
import { AuthService } from "@services/auth/auth.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { WelcomeDialogService } from "./welcome-dialog.service";

describe("WelcomeDialogService", () => {
  let dialogMock: Pick<MatDialog, "open">;
  let authMock: MockAuthService;

  beforeEach(() => {
    dialogMock = { open: jest.fn() } as unknown as Pick<MatDialog, "open">;

    TestBed.configureTestingModule({
      providers: [
        WelcomeDialogService,
        { provide: MatDialog, useValue: dialogMock },
        { provide: AuthService, useClass: MockAuthService }
      ]
    });
    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  it("opens dialog when authenticated and not explicitly hidden by status===3", () => {
    authMock.isAuthenticated.set(true);
    authMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      hide_welcome: false,
      subscription_status: 2
    });
    const service = TestBed.inject(WelcomeDialogService);
    TestBed.tick();

    expect(service.opened()).toBe(true);
  });

  it("does NOT open when hideWelcome is true and subscriptionStatus===3", () => {
    authMock.isAuthenticated.set(true);
    authMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      hide_welcome: true,
      subscription_status: 3
    });
    const service = TestBed.inject(WelcomeDialogService);
    TestBed.tick();

    expect(service.opened()).toBe(false);
  });

  it("does NOT open when not authenticated", () => {
    authMock.isAuthenticated.set(false);
    const service = TestBed.inject(WelcomeDialogService);
    TestBed.tick();

    expect(service.opened()).toBe(false);
  });
});
