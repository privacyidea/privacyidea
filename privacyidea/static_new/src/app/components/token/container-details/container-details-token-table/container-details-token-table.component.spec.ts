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
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { of, Subject } from "rxjs";
import { signal } from "@angular/core";
import { MatTableDataSource } from "@angular/material/table";
import { NavigationEnd, Router } from "@angular/router";

import { ContainerDetailsTokenTableComponent } from "./container-details-token-table.component";
import {
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockNotificationService,
  MockOverflowService,
  MockTableUtilsService,
  MockTokenService
} from "../../../../../testing/mock-services";
import { AuthService } from "../../../../services/auth/auth.service";
import { ContainerService } from "../../../../services/container/container.service";
import { TokenService } from "../../../../services/token/token.service";
import { TableUtilsService } from "../../../../services/table-utils/table-utils.service";
import { OverflowService } from "../../../../services/overflow/overflow.service";
import { NotificationService } from "../../../../services/notification/notification.service";
import { MatDialog } from "@angular/material/dialog";
import { UserService } from "../../../../services/user/user.service";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { ContentService } from "../../../../services/content/content.service";

import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";

const routerEvents$ = new Subject<NavigationEnd>();
routerEvents$.next(new NavigationEnd(1, "/", "/"));
const routerMock = {
  navigate: jest.fn().mockResolvedValue(true),
  url: "/",
  events: routerEvents$
} as unknown as jest.Mocked<Router>;

function makeDialogResult(result: boolean) {
  return { afterClosed: () => of(result) } as any;
}

const matDialogMock = {
  open: jest.fn().mockReturnValue(makeDialogResult(true))
};

describe("ContainerDetailsTokenTableComponent", () => {
  let fixture: ComponentFixture<ContainerDetailsTokenTableComponent>;
  let component: ContainerDetailsTokenTableComponent;

  let containerServiceMock: MockContainerService;
  let tokenServiceMock: MockTokenService;
  const overflowServiceMock = new MockOverflowService();
  const tableUtilsMock = new MockTableUtilsService();
  const notificationServiceMock = new MockNotificationService();

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsTokenTableComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: TableUtilsService, useValue: tableUtilsMock },
        { provide: OverflowService, useValue: overflowServiceMock },
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: Router, useValue: routerMock },
        { provide: MatDialog, useValue: matDialogMock },
        { provide: UserService, useClass: class {} },
        { provide: ContentService, useClass: MockContentService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsTokenTableComponent);
    component = fixture.componentInstance;

    containerServiceMock = TestBed.inject(ContainerService) as unknown as MockContainerService;
    tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;

    component.containerTokenData = signal(
      new MatTableDataSource<any>([
        {
          serial: "Mock serial",
          tokentype: "hotp",
          active: true,
          username: "userA"
        },
        {
          serial: "Another serial",
          tokentype: "totp",
          active: false,
          username: "userB"
        }
      ])
    );

    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("creates the component", () => {
    expect(component).toBeTruthy();
  });

  it("adds remove/delete columns when actionAllowed is true (constructor logic)", () => {
    const auth = TestBed.inject(AuthService) as any;
    jest.spyOn(auth, "actionAllowed").mockReturnValue(true);

    const fx = TestBed.createComponent(ContainerDetailsTokenTableComponent);
    const cmp = fx.componentInstance;

    expect(cmp.displayedColumns).toEqual(expect.arrayContaining(["remove", "delete"]));
  });

  it("sets paginator and sort on both internal and external data sources", () => {
    const ds = component.containerTokenData();
    expect(ds.paginator).toBe(component.paginator);
    expect(ds.sort).toBe(component.sort);
  });

  it("updates filterValue & sets filter on both internal and external data sources", () => {
    const mockEvent = { target: { value: " testFilter " } } as unknown as Event;
    component.handleFilterInput(mockEvent);

    expect(component.filterValue()).toBe("testFilter");
    expect(component.dataSource.filter).toBe("testfilter");
    expect(component.containerTokenData().filter).toBe("testfilter");
  });

  it("delegates to toggleActive when columnKey === 'active'", () => {
    const toggleSpy = jest.spyOn(component, "toggleActive");
    const row = { serial: "Mock serial", active: true };
    component.handleColumnClick("active", row as any);
    expect(toggleSpy).toHaveBeenCalledWith(row);
  });

  it("does nothing when columnKey !== 'active'", () => {
    const toggleSpy = jest.spyOn(component, "toggleActive");
    component.handleColumnClick("username", {} as any);
    expect(toggleSpy).not.toHaveBeenCalled();
  });

  it("isAssignableToAllToken true when assigned user is set and at least one token is unassigned", () => {
    containerServiceMock.containerDetail.set({
      containers: [
        {
          serial: "CONT-1",
          users: [{ user_name: "alice", user_realm: "r1", user_resolver: "", user_id: "" }],
          tokens: [],
          realms: [],
          states: [],
          type: "",
          select: "",
          description: ""
        }
      ],
      count: 1
    });

    const ds = component.containerTokenData();
    ds.data = [
      { serial: "S1", username: "bob", active: true },
      { serial: "S2", username: "", active: true }
    ] as any;
    fixture.detectChanges();

    expect(component.isAssignableToAllToken()).toBe(true);
  });

  it("isUnassignableFromAllToken true when any token has a username", () => {
    const ds = component.containerTokenData();
    ds.data = [
      { serial: "S1", username: "", active: true },
      { serial: "S2", username: "bob", active: true }
    ] as any;
    fixture.detectChanges();

    expect(component.isUnassignableFromAllToken()).toBe(true);
  });

  it("isUnassignableFromAllToken false when all tokens are unassigned", () => {
    const ds = component.containerTokenData();
    ds.data = [
      { serial: "S1", username: "", active: true },
      { serial: "S2", username: "", active: true }
    ] as any;
    fixture.detectChanges();

    expect(component.isUnassignableFromAllToken()).toBe(false);
  });

  it("toggleActive calls service then reloads container details", () => {
    const t = { serial: "Mock serial", active: true } as any;
    jest.spyOn(tokenServiceMock, "toggleActive");

    component.toggleActive(t);
    expect(tokenServiceMock.toggleActive).toHaveBeenCalledWith("Mock serial", true);
    expect(containerServiceMock.containerDetailResource.reload).toHaveBeenCalledTimes(1);
  });

  it("removeTokenFromContainer confirms and removes on confirm=true", () => {
    jest
      .spyOn(containerServiceMock, "removeTokenFromContainer")
      .mockReturnValue(of({ result: { value: true } } as any));
    component.removeTokenFromContainer("CONT-1", "Mock serial");
    expect(matDialogMock.open).toHaveBeenCalledWith(
      ConfirmationDialogComponent,
      expect.objectContaining({
        data: expect.objectContaining({
          serialList: ["Mock serial"],
          action: "remove"
        })
      })
    );
    expect(containerServiceMock.removeTokenFromContainer).toHaveBeenCalledWith("CONT-1", "Mock serial");
    expect(containerServiceMock.containerDetailResource.reload).toHaveBeenCalled();
  });

  it("removeTokenFromContainer does nothing when confirm=false", () => {
    matDialogMock.open.mockReturnValueOnce(makeDialogResult(false));
    component.removeTokenFromContainer("CONT-1", "Mock serial");
    expect(containerServiceMock.removeTokenFromContainer).not.toHaveBeenCalled();
  });

  it("deleteTokenFromContainer confirms and deletes on confirm=true", () => {
    component.deleteTokenFromContainer("Another serial");
    expect(matDialogMock.open).toHaveBeenCalledWith(
      ConfirmationDialogComponent,
      expect.objectContaining({
        data: expect.objectContaining({
          serialList: ["Another serial"],
          action: "delete"
        })
      })
    );
    expect(tokenServiceMock.deleteToken as any).toHaveBeenCalledWith("Another serial");
    expect(containerServiceMock.containerDetailResource.reload).toHaveBeenCalled();
  });
});
