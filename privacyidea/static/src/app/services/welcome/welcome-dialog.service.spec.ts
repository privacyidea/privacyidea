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
import { FreeTierDialogComponent } from "@components/shared/free-tier-dialog/free-tier-dialog.component";
import { WelcomeDialogComponent } from "@components/shared/welcome-dialog/welcome-dialog.component";
import { AuthData, AuthService } from "@services/auth/auth.service";
import { Subject } from "rxjs";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { WelcomeDialogService } from "./welcome-dialog.service";

describe("WelcomeDialogService", () => {
  let dialogMock: { open: jest.Mock };
  let authMock: MockAuthService;
  let welcomeClosed: Subject<void>;

  const openedDialogs = () => dialogMock.open.mock.calls.map(([component]) => component);

  // An interactive login: authenticated only after the service was created.
  const login = (authData: Partial<AuthData>): WelcomeDialogService => {
    authMock.isAuthenticated.set(false);
    const service = TestBed.inject(WelcomeDialogService);
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, ...authData });
    authMock.isAuthenticated.set(true);
    TestBed.tick();
    return service;
  };

  beforeEach(() => {
    welcomeClosed = new Subject<void>();
    dialogMock = { open: jest.fn(() => ({ afterClosed: () => welcomeClosed })) };

    TestBed.configureTestingModule({
      providers: [
        WelcomeDialogService,
        { provide: MatDialog, useValue: dialogMock },
        { provide: AuthService, useClass: MockAuthService }
      ]
    });
    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
  });

  it("opens dialog on an interactive login (auth transitions to true after init)", () => {
    authMock.isAuthenticated.set(false);
    const service = TestBed.inject(WelcomeDialogService);

    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, hide_welcome: false });
    authMock.isAuthenticated.set(true);
    TestBed.tick();

    expect(service.opened()).toBe(true);
    expect(dialogMock.open).toHaveBeenCalled();
  });

  it("does NOT open on login when hideWelcome is true", () => {
    authMock.isAuthenticated.set(false);
    const service = TestBed.inject(WelcomeDialogService);

    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, hide_welcome: true });
    authMock.isAuthenticated.set(true);
    TestBed.tick();

    expect(service.opened()).toBe(false);
    expect(dialogMock.open).not.toHaveBeenCalled();
  });

  it("shows the free tier dialog after the welcome dialog when the free tier is exceeded", () => {
    const service = login({ hide_welcome: false, subscription_status: 1 });

    expect(service.opened()).toBe(true);
    expect(openedDialogs()).toEqual([WelcomeDialogComponent]);

    welcomeClosed.next();
    expect(openedDialogs()).toEqual([WelcomeDialogComponent, FreeTierDialogComponent]);
  });

  it("does not open the free tier dialog when the welcome dialog is closed by a logout", () => {
    login({ hide_welcome: false, subscription_status: 1 });

    authMock.authData.set(null);
    authMock.isAuthenticated.set(false);
    TestBed.tick();
    welcomeClosed.next();

    expect(openedDialogs()).toEqual([WelcomeDialogComponent]);
  });

  it("does not open the free tier dialog of a previous session after the next login", () => {
    login({ hide_welcome: false, subscription_status: 1 });

    authMock.authData.set(null);
    authMock.isAuthenticated.set(false);
    TestBed.tick();
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, hide_welcome: true, subscription_status: 0 });
    authMock.isAuthenticated.set(true);
    TestBed.tick();
    welcomeClosed.next();

    expect(openedDialogs()).toEqual([WelcomeDialogComponent]);
  });

  it("shows only the free tier dialog when hideWelcome hides the welcome dialog", () => {
    const service = login({ hide_welcome: true, subscription_status: 1 });

    expect(service.opened()).toBe(true);
    expect(openedDialogs()).toEqual([FreeTierDialogComponent]);
  });

  it.each([0, 2, 3])("shows only the welcome dialog at subscription status %i", (subscription_status) => {
    login({ hide_welcome: false, subscription_status });
    welcomeClosed.next();

    expect(openedDialogs()).toEqual([WelcomeDialogComponent]);
  });

  it.each([0, 2, 3])("shows no dialog with hideWelcome at subscription status %i", (subscription_status) => {
    const service = login({ hide_welcome: true, subscription_status });

    expect(service.opened()).toBe(false);
    expect(dialogMock.open).not.toHaveBeenCalled();
  });

  it("shows no free tier dialog to a self-service user", () => {
    const service = login({ role: "user", hide_welcome: true, subscription_status: 1 });

    expect(service.opened()).toBe(false);
    expect(dialogMock.open).not.toHaveBeenCalled();
  });

  it("does NOT open when not authenticated", () => {
    authMock.isAuthenticated.set(false);
    const service = TestBed.inject(WelcomeDialogService);
    TestBed.tick();

    expect(service.opened()).toBe(false);
  });

  it("does NOT re-open for a session already authenticated at startup (restored on reload)", () => {
    // Authenticated before the service is constructed = a restored session, not a fresh login.
    authMock.isAuthenticated.set(true);
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, hide_welcome: false });
    const service = TestBed.inject(WelcomeDialogService);
    TestBed.tick();

    expect(service.opened()).toBe(false);
    expect(dialogMock.open).not.toHaveBeenCalled();
  });

  it("does NOT open on an interactive login of a self-service user", () => {
    authMock.isAuthenticated.set(false);
    const service = TestBed.inject(WelcomeDialogService);

    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, role: "user", hide_welcome: false });
    authMock.isAuthenticated.set(true);
    TestBed.tick();

    expect(service.opened()).toBe(false);
    expect(dialogMock.open).not.toHaveBeenCalled();
  });
});
