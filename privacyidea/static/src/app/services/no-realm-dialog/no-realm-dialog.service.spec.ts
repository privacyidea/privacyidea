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
import { Subject } from "rxjs";
import { AuthService } from "@services/auth/auth.service";
import { RealmService } from "@services/realm/realm.service";
import { ResolverService } from "@services/resolver/resolver.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockRealmService } from "@testing/mock-services/mock-realm-service";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { NoRealmDialogService } from "./no-realm-dialog.service";

describe("NoRealmDialogService", () => {
  let dialogMock: { open: jest.Mock; openDialogs: unknown[]; afterAllClosed: Subject<void> };
  let authMock: MockAuthService;
  let realmMock: MockRealmService;
  let resolverMock: MockResolverService;

  const start = (): void => {
    TestBed.inject(NoRealmDialogService);
    TestBed.tick();
  };

  beforeEach(() => {
    dialogMock = { open: jest.fn(), openDialogs: [], afterAllClosed: new Subject<void>() };
    TestBed.configureTestingModule({
      providers: [
        NoRealmDialogService,
        { provide: MatDialog, useValue: dialogMock },
        { provide: AuthService, useClass: MockAuthService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: ResolverService, useClass: MockResolverService }
      ]
    });
    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    realmMock = TestBed.inject(RealmService) as unknown as MockRealmService;
    resolverMock = TestBed.inject(ResolverService) as unknown as MockResolverService;
    authMock.isAuthenticated.set(true);
    realmMock.noRealm.set(true);
    authMock.actionAllowed.mockImplementation((action: string) => action === "resolverwrite");
  });

  it.each<{ name: string; resolvers: string[]; noResolver: boolean }>([
    { name: "the no-resolver variant when no resolver exists", resolvers: [], noResolver: true },
    { name: "the realm variant when a resolver exists", resolvers: ["reso1"], noResolver: false }
  ])("opens for an admin with the right while no realm exists, as $name", ({ resolvers, noResolver }) => {
    if (resolvers.length) resolverMock.setResolverOptions(resolvers);
    start();
    expect(dialogMock.open).toHaveBeenCalledTimes(1);
    expect(dialogMock.open).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ data: { noResolver } }));
    if (noResolver) expect(resolverMock.loadRequested()).toBe(true);
  });

  it("waits for the resolver list before opening", () => {
    resolverMock.resolversResource.isLoading.set(true);
    start();
    expect(dialogMock.open).not.toHaveBeenCalled();
    resolverMock.resolversResource.isLoading.set(false);
    TestBed.tick();
    expect(dialogMock.open).toHaveBeenCalledTimes(1);
  });

  it("opens only once per session and again after a new login", () => {
    start();
    TestBed.tick();
    expect(dialogMock.open).toHaveBeenCalledTimes(1);
    authMock.isAuthenticated.set(false);
    TestBed.tick();
    authMock.isAuthenticated.set(true);
    TestBed.tick();
    expect(dialogMock.open).toHaveBeenCalledTimes(2);
  });

  it("waits for an open dialog to close before opening, while the session stays authenticated", () => {
    dialogMock.openDialogs.push({});
    start();
    expect(dialogMock.open).not.toHaveBeenCalled();
    dialogMock.openDialogs.pop();
    dialogMock.afterAllClosed.next();
    expect(dialogMock.open).toHaveBeenCalledTimes(1);
    expect(dialogMock.open).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ data: { noResolver: true } })
    );
  });

  it("does not open after a logout while it waited for another dialog", () => {
    dialogMock.openDialogs.push({});
    start();
    authMock.isAuthenticated.set(false);
    TestBed.tick();
    dialogMock.openDialogs.pop();
    dialogMock.afterAllClosed.next();
    expect(dialogMock.open).not.toHaveBeenCalled();
  });

  it("does not open from the deferred callback when the conditions no longer hold", () => {
    dialogMock.openDialogs.push({});
    start();
    authMock.isAuthenticated.set(false);
    dialogMock.openDialogs.pop();
    dialogMock.afterAllClosed.next();
    expect(dialogMock.open).not.toHaveBeenCalled();
  });

  it.each<{ name: string; arrange: () => void }>([
    { name: "a realm exists", arrange: () => realmMock.noRealm.set(false) },
    { name: "the resolverwrite right is missing", arrange: () => authMock.actionAllowed.mockReturnValue(false) },
    { name: "the user is a non-admin", arrange: () => authMock.role.set("user") },
    { name: "not authenticated", arrange: () => authMock.isAuthenticated.set(false) }
  ])("does not open when $name", ({ arrange }) => {
    arrange();
    start();
    expect(dialogMock.open).not.toHaveBeenCalled();
  });
});
