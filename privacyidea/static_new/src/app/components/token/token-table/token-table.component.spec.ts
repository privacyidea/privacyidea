/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { TokenTableComponent } from "./token-table.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { of } from "rxjs";
import {
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockPiResponse,
  MockTableUtilsService,
  MockTokenService
} from "../../../../testing/mock-services";
import { TokenTableSelfServiceComponent } from "./token-table.self-service.component";
import { TokenService } from "../../../services/token/token.service";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { ContentService } from "../../../services/content/content.service";
import { AuthService, JwtData } from "../../../services/auth/auth.service";
import { ContainerService } from "../../../services/container/container.service";
import { MatDialog } from "@angular/material/dialog";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockAuthService } from "../../../../testing/mock-services/mock-auth-service";

class MatDialogMock {
  result = true;
  open = jest.fn(() => ({
    afterClosed: () => of(this.result)
  }));
}

describe("TokenTableComponent + TokenTableSelfServiceComponent", () => {
  let tableFixture: ComponentFixture<TokenTableComponent>;
  let table: TokenTableComponent;

  let selfFixture: ComponentFixture<TokenTableSelfServiceComponent>;
  let self: TokenTableSelfServiceComponent;

  let tokenService: MockTokenService;
  let auth: MockAuthService;
  let matDialog: MatDialogMock;

  beforeAll(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (q: string) => ({
        matches: false,
        media: q,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn()
      })
    });

    class RO {
      observe = jest.fn();
      unobserve = jest.fn();
      disconnect = jest.fn();
    }

    (globalThis as any).ResizeObserver = RO;

    if (!(globalThis as any).MutationObserver) {
      (globalThis as any).MutationObserver = class {
        observe() {}

        disconnect() {}

        takeRecords() {
          return [];
        }
      };
    }

    jest.spyOn(console, "warn").mockImplementation(() => {});
  });

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenTableComponent, TokenTableSelfServiceComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: ContentService, useClass: MockContentService },
        {
          provide: DialogService,
          useValue: {
            /* not used here */
          }
        },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: MatDialog, useClass: MatDialogMock },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    tableFixture = TestBed.createComponent(TokenTableComponent);
    table = tableFixture.componentInstance;

    selfFixture = TestBed.createComponent(TokenTableSelfServiceComponent);
    self = selfFixture.componentInstance;

    tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    auth = TestBed.inject(AuthService) as unknown as MockAuthService;
    matDialog = TestBed.inject(MatDialog) as unknown as MatDialogMock;

    tokenService.toggleActive.mockReturnValue(of({}));
    tokenService.resetFailCount.mockReturnValue(of(null));
    (tokenService as any).revokeToken = jest.fn().mockReturnValue(of({}));
    (tokenService as any).deleteToken = jest.fn().mockReturnValue(of({}));
    auth.actionAllowed.mockImplementation((action: string) => auth.jwtData()?.rights?.includes(action));

    tableFixture.detectChanges();
    selfFixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("TokenTableComponent should create", () => {
    expect(table).toBeTruthy();
  });

  it("TokenTableSelfServiceComponent should create", () => {
    expect(self).toBeTruthy();
  });

  it("isAllSelected/toggleAllRows/toggleRow work as expected", () => {
    const tokens = [{ serial: "T-1" } as any, { serial: "T-2" } as any];
    tokenService.tokenResource.set(
      MockPiResponse.fromValue({
        tokens,
        count: 2,
        current: 1
      })
    );
    tableFixture.detectChanges();

    expect(table.isAllSelected()).toBe(false);

    table.toggleAllRows();
    expect(table.tokenSelection()).toEqual(tokens);
    expect(table.isAllSelected()).toBe(true);

    table.toggleRow(tokens[0]);
    expect(table.tokenSelection()).toEqual([tokens[1]]);
    expect(table.isAllSelected()).toBe(false);

    table.toggleRow(tokens[0]);
    expect(table.tokenSelection()).toEqual(tokens.reverse());

    table.toggleAllRows();
    expect(table.tokenSelection()).toEqual([]);
  });

  it("toggleActive calls service and reloads when allowed & not revoked/locked", () => {
    const t = { serial: "A", active: true, revoked: false, locked: false } as any;
    auth.jwtData.set({
      ...auth.jwtData(),
      rights: ["disable", "enable"]
    } as JwtData);

    table.toggleActive(t);

    expect(tokenService.toggleActive).toHaveBeenCalledWith("A", true);
    expect(tokenService.tokenResource.reload).toHaveBeenCalledTimes(1);
  });

  it("toggleActive does nothing if action not allowed", () => {
    const t = { serial: "A", active: true, revoked: false, locked: false } as any;
    auth.jwtData.set({
      ...auth.jwtData(),
      rights: []
    } as JwtData);

    table.toggleActive(t);

    expect(tokenService.toggleActive).not.toHaveBeenCalled();
    expect(tokenService.tokenResource.reload).not.toHaveBeenCalled();
  });

  it("toggleActive does nothing if revoked or locked", () => {
    auth.jwtData.set({
      ...auth.jwtData(),
      rights: ["disable", "enable"]
    } as JwtData);

    table.toggleActive({ serial: "X", active: true, revoked: true, locked: false } as any);
    table.toggleActive({ serial: "Y", active: false, revoked: false, locked: true } as any);

    expect(tokenService.toggleActive).not.toHaveBeenCalled();
  });

  it("resetFailCount calls service and reloads when allowed & not revoked/locked", () => {
    const t = { serial: "B", revoked: false, locked: false } as any;
    auth.jwtData.set({
      ...auth.jwtData(),
      rights: ["reset"]
    } as JwtData);

    table.resetFailCount(t);

    expect(tokenService.resetFailCount).toHaveBeenCalledWith("B");
    expect(tokenService.tokenResource.reload).toHaveBeenCalledTimes(1);
  });

  it("resetFailCount does nothing when action not allowed / revoked / locked", () => {
    auth.jwtData.set({
      ...auth.jwtData(),
      rights: []
    } as JwtData);
    table.resetFailCount({ serial: "B", revoked: false, locked: false } as any);
    expect(tokenService.resetFailCount).not.toHaveBeenCalled();

    auth.jwtData.set({
      ...auth.jwtData(),
      rights: ["reset"]
    } as JwtData);
    table.resetFailCount({ serial: "B", revoked: true, locked: false } as any);
    table.resetFailCount({ serial: "B", revoked: false, locked: true } as any);
    expect(tokenService.resetFailCount).not.toHaveBeenCalled();
  });

  it("onPageEvent updates page size, index and service's eventPageSize", () => {
    table.onPageEvent({ pageIndex: 2, pageSize: 25, length: 100 } as any);
    expect(tokenService.eventPageSize).toBe(25);
    expect(table.pageSize()).toBe(25);
    expect(table.pageIndex()).toBe(2);
  });

  it("onSortEvent sets default when direction empty, else sets provided sort", () => {
    table.onSortEvent({ active: "failcount", direction: "" } as any);
    expect(table.sort()).toEqual({ active: "serial", direction: "asc" });

    table.onSortEvent({ active: "description", direction: "desc" } as any);
    expect(table.sort()).toEqual({ active: "description", direction: "desc" });
  });

  it("tokenDataSource/totalLength reflect tokenResource; fall back to empty skeleton when undefined", () => {
    const initial = table.tokenDataSource().data;
    expect(Array.isArray(initial)).toBe(true);
    expect(initial.length).toBe(table.pageSize());

    const tokens = [{ serial: "S-1" }, { serial: "S-2" }] as any;
    tokenService.tokenResource.set(MockPiResponse.fromValue({ tokens, count: 2, current: 1 }));
    tableFixture.detectChanges();

    expect(table.tokenDataSource().data).toEqual(tokens);
    expect(table.totalLength()).toBe(2);
  });

  it("self-service column keys include revoke/delete depending on permissions", () => {
    auth.jwtData.set({
      ...auth.jwtData(),
      rights: ["revoke", "delete"]
    } as JwtData);

    const f1 = TestBed.createComponent(TokenTableSelfServiceComponent);
    const c1 = f1.componentInstance;

    expect(c1.columnKeysSelfService).toEqual(
      expect.arrayContaining([
        "serial",
        "tokentype",
        "description",
        "container_serial",
        "active",
        "failcount",
        "revoke",
        "delete"
      ])
    );

    auth.jwtData.set({
      ...auth.jwtData(),
      rights: []
    } as JwtData);

    const f2 = TestBed.createComponent(TokenTableSelfServiceComponent);
    const c2 = f2.componentInstance;

    expect(c2.columnKeysSelfService).toEqual(
      expect.arrayContaining(["serial", "tokentype", "description", "container_serial", "active", "failcount"])
    );
    expect(c2.columnKeysSelfService).not.toEqual(expect.arrayContaining(["revoke", "delete"]));
  });

  it("revokeToken: always calls service; reloads only when dialog returns true", () => {
    const serial = "R-1";

    matDialog.result = true;
    self.revokeToken(serial);
    expect(matDialog.open).toHaveBeenCalledTimes(1);
    expect((tokenService as any).revokeToken).toHaveBeenCalledWith(serial);
    expect(tokenService.tokenResource.reload).toHaveBeenCalledTimes(1);

    jest.clearAllMocks();

    matDialog.result = false;
    self.revokeToken(serial);
    expect(matDialog.open).toHaveBeenCalledTimes(1);
    expect((tokenService as any).revokeToken).toHaveBeenCalledWith(serial);
    expect(tokenService.tokenResource.reload).not.toHaveBeenCalled();
  });

  it("deleteToken: always calls service; reloads only when dialog returns true", () => {
    const serial = "D-1";

    matDialog.result = true;
    self.deleteToken(serial);
    expect(matDialog.open).toHaveBeenCalledTimes(1);
    expect((tokenService as any).deleteToken).toHaveBeenCalledWith(serial);
    expect(tokenService.tokenResource.reload).toHaveBeenCalledTimes(1);

    jest.clearAllMocks();

    matDialog.result = false;
    self.deleteToken(serial);
    expect(matDialog.open).toHaveBeenCalledTimes(1);
    expect((tokenService as any).deleteToken).toHaveBeenCalledWith(serial);
    expect(tokenService.tokenResource.reload).not.toHaveBeenCalled();
  });
});
