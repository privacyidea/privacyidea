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

import {
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockTableUtilsService,
  MockTokenService,
  MockUserService
} from "@testing/mock-services";
import { UserDetailsTokenTableComponent } from "./user-details-token-table.component";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { ContainerDetailToken } from "@services/container/container.service";
import { TokenDetails, TokenService, Tokens } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";

import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";

describe("UserDetailsTokenTableComponent", () => {
  let fixture: ComponentFixture<UserDetailsTokenTableComponent>;
  let component: UserDetailsTokenTableComponent;

  let tokenServiceMock: MockTokenService;

  beforeEach(async () => {
    TestBed.resetTestingModule();

    await TestBed.configureTestingModule({
      imports: [UserDetailsTokenTableComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: ContentService, useClass: MockContentService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: UserService, useClass: MockUserService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;

    fixture = TestBed.createComponent(UserDetailsTokenTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("has the select column prepended to the data columns", () => {
    expect(component.displayedColumns).toEqual([
      "select",
      "serial",
      "tokentype",
      "active",
      "description",
      "failcount",
      "maxfail",
      "container_serial"
    ]);
  });

  it("wires sort in ngAfterViewInit", () => {
    expect(component.dataSource.sort).toBe(component.sort);
  });

  it("populates dataSource from userTokenResource via linkedSignal", () => {
    tokenServiceMock.userTokenResource.value.set(
      MockPiResponse.fromValue<Tokens>({
        count: 2,
        current: 2,
        tokens: [
          {
            serial: "T-1",
            tokentype: "hotp",
            active: true,
            revoked: false,
            locked: false,
            description: "alpha",
            failcount: 0,
            maxfail: 10,
            container_serial: "C-1",
            user_realm: "r1",
            username: "alice",
            resolver: ""
          },
          {
            serial: "T-2",
            tokentype: "totp",
            active: false,
            revoked: false,
            locked: false,
            description: "beta",
            failcount: 2,
            maxfail: 10,
            container_serial: "C-2",
            user_realm: "r1",
            username: "alice",
            resolver: ""
          }
        ] as TokenDetails[]
      })
    );

    fixture.detectChanges();

    expect(component.dataSource.data.map((t: ContainerDetailToken) => t.serial)).toEqual(["T-1", "T-2"]);
  });

  it("keeps previous list when userTokenResource is missing (linkedSignal fallback)", () => {
    tokenServiceMock.userTokenResource.value.set(
      MockPiResponse.fromValue<Tokens>({
        count: 1,
        current: 1,
        tokens: [
          {
            serial: "KEEP-ME",
            tokentype: "hotp",
            active: true,
            revoked: false,
            locked: false,
            description: "",
            failcount: 0,
            maxfail: 10,
            container_serial: "C-X",
            user_realm: "r1",
            username: "alice",
            resolver: ""
          }
        ] as TokenDetails[]
      })
    );
    fixture.detectChanges();
    expect(component.dataSource.data.map((t: ContainerDetailToken) => t.serial)).toEqual(["KEEP-ME"]);

    tokenServiceMock.userTokenResource.value.set(undefined);
    fixture.detectChanges();

    expect(component.dataSource.data.map((t: ContainerDetailToken) => t.serial)).toEqual(["KEEP-ME"]);
  });

  it("toggleRow adds and removes a row from the selection", () => {
    const rowA = { serial: "A" } as unknown as ContainerDetailToken;
    const rowB = { serial: "B" } as unknown as ContainerDetailToken;

    component.toggleRow(rowA);
    expect(component.selection()).toEqual([rowA]);

    component.toggleRow(rowB);
    expect(component.selection()).toEqual([rowA, rowB]);

    component.toggleRow(rowA);
    expect(component.selection()).toEqual([rowB]);
  });

  it("toggleAllRows selects all rows and clears when all are selected", () => {
    const rowA = { serial: "A" } as unknown as ContainerDetailToken;
    const rowB = { serial: "B" } as unknown as ContainerDetailToken;
    component.dataSource.data = [rowA, rowB];

    expect(component.isAllSelected()).toBe(false);

    component.toggleAllRows();
    expect(component.selection()).toEqual([rowA, rowB]);
    expect(component.isAllSelected()).toBe(true);

    component.toggleAllRows();
    expect(component.selection()).toEqual([]);
    expect(component.isAllSelected()).toBe(false);
  });

  it("deleteSelected calls bulkDeleteWithConfirmDialog with the selected serials", () => {
    const rowA = { serial: "A" } as unknown as ContainerDetailToken;
    const rowB = { serial: "B" } as unknown as ContainerDetailToken;
    component.selection.set([rowA, rowB]);

    component.deleteSelected();

    expect(tokenServiceMock.bulkDeleteWithConfirmDialog).toHaveBeenCalledWith(["A", "B"], expect.any(Function));
    const afterDelete = (tokenServiceMock.bulkDeleteWithConfirmDialog as jest.Mock).mock.calls[0][1];
    afterDelete();
    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
  });

  it("unassignSelected unassigns each selected token and reloads", () => {
    const rowA = { serial: "A" } as unknown as ContainerDetailToken;
    const rowB = { serial: "B" } as unknown as ContainerDetailToken;
    component.selection.set([rowA, rowB]);

    component.unassignSelected();

    expect(tokenServiceMock.unassignUser).toHaveBeenCalledWith("A");
    expect(tokenServiceMock.unassignUser).toHaveBeenCalledWith("B");
    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
  });

  it("toggleActiveSelected toggles each selected token and reloads", () => {
    const rowA = { serial: "A", active: true } as unknown as ContainerDetailToken;
    const rowB = { serial: "B", active: false } as unknown as ContainerDetailToken;
    component.selection.set([rowA, rowB]);

    component.toggleActiveSelected();

    expect(tokenServiceMock.toggleActive).toHaveBeenCalledWith("A", true);
    expect(tokenServiceMock.toggleActive).toHaveBeenCalledWith("B", false);
    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
  });

  it("resetFailcountSelected resets each selected token and reloads", () => {
    const rowA = { serial: "A" } as unknown as ContainerDetailToken;
    const rowB = { serial: "B" } as unknown as ContainerDetailToken;
    component.selection.set([rowA, rowB]);

    component.resetFailcountSelected();

    expect(tokenServiceMock.resetFailCount).toHaveBeenCalledWith("A");
    expect(tokenServiceMock.resetFailCount).toHaveBeenCalledWith("B");
    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
  });
});
