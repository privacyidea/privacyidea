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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatTableDataSource } from "@angular/material/table";
import { provideRouter } from "@angular/router";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { AuthService } from "@services/auth/auth.service";
import { ContainerDetailToken, ContainerService } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokenService } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { expectsTableStateGating } from "@testing/table-state-gating";
import {
  MockContainerService,
  MockContentService,
  MockDialogService,
  MockLocalService,
  MockNotificationService,
  MockTableUtilsService,
  MockTokenService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { Subject, of } from "rxjs";
import { ContainerDetailsTokenTableComponent } from "./container-details-token-table.component";
import { axe } from "@testing/axe";

describe("ContainerDetailsTokenTableComponent", () => {
  let fixture: ComponentFixture<ContainerDetailsTokenTableComponent>;
  let component: ContainerDetailsTokenTableComponent;

  let containerServiceMock: MockContainerService;
  let tokenServiceMock: MockTokenService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsTokenTableComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: NotificationService, useClass: MockNotificationService },
        provideRouter([]),
        { provide: UserService, useClass: class {} },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService },
        MockLocalService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsTokenTableComponent);
    component = fixture.componentInstance;

    containerServiceMock = TestBed.inject(ContainerService) as unknown as MockContainerService;
    tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;

    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    confirmClosed = new Subject();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);

    fixture.componentRef.setInput(
      "containerTokenData",
      new MatTableDataSource<ContainerDetailToken>([
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
      ] as ContainerDetailToken[])
    );

    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  describe("token rows", () => {
    const showTokens = (role: "admin" | "user") => {
      (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
        ...MockAuthService.MOCK_AUTH_DATA,
        role,
        username: "userA",
        rights: ["container_list"]
      });
      fixture.componentRef.setInput(
        "containerTokenData",
        new MatTableDataSource([
          { serial: "T-1", tokentype: "hotp", active: true, username: "userA", user_realm: "r1" }
        ] as ContainerDetailToken[])
      );
      fixture.detectChanges();
    };
    const linkWithText = (text: string): HTMLAnchorElement | undefined =>
      Array.from<HTMLAnchorElement>(fixture.nativeElement.querySelectorAll("tbody a")).find(
        (a) => a.textContent?.trim() === text
      );

    it.each(["admin", "user"] as const)("passes the axe accessibility checks for the %s", async (role) => {
      (TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService).getDisplayText.mockReturnValue("Active");
      showTokens(role);

      expect(await axe(fixture.nativeElement)).toHaveNoViolations();
    });

    it("reloads the container details once the token state was toggled", () => {
      (TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService).canToggleActive.mockReturnValue(true);
      showTokens("user");

      fixture.nativeElement.querySelector("td.mat-column-active button").click();

      expect(tokenServiceMock.toggleActive).toHaveBeenCalledWith("T-1", true);
      expect(containerServiceMock.containerDetailsResource.reload).toHaveBeenCalledTimes(1);
    });

    it("links the token serial to the token details", () => {
      showTokens("user");

      expect(linkWithText("T-1")?.getAttribute("href")).toBe("/tokens/details/T-1");
    });

    it("links admins to the details of the token owner in their realm", () => {
      showTokens("admin");

      expect(linkWithText("userA")?.getAttribute("href")).toBe("/users/details/userA?realm=r1");
    });

    it("shows users the token owner as text, since they cannot open user details", () => {
      showTokens("user");

      expect(linkWithText("userA")).toBeUndefined();
      expect(fixture.nativeElement.querySelector("tbody").textContent).toContain("userA");
    });
  });

  it("leaves the empty state once rows appear on the kept data source", () => {
    // The data source is mutated in place and the same reference returned, so the table state can
    // only see new rows if that signal still reports a change.
    (TestBed.inject(AuthService) as unknown as MockAuthService).authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["container_list"]
    });
    fixture.componentRef.setInput("containerTokenData", new MatTableDataSource([] as never[]));
    fixture.detectChanges();
    expect(component.tableState.status()).toBe("empty");

    fixture.componentRef.setInput("containerTokenData", new MatTableDataSource([{ serial: "T-NEW" }] as never[]));
    fixture.detectChanges();

    expect(component.dataSource().data.length).toBe(1);
    expect(component.tableState.status()).toBe("ready");
  });

  it("gates the table on its read right, row count and filter", () => {
    expectsTableStateGating({
      state: component.tableState,
      right: "container_list"
    });
  });

  it("creates the component", () => {
    expect(component).toBeTruthy();
  });

  it("adds remove/delete columns when actionAllowed is true (constructor logic)", () => {
    const auth = TestBed.inject(AuthService) as unknown as MockAuthService;
    jest.spyOn(auth, "actionAllowed").mockReturnValue(true);

    const fx = TestBed.createComponent(ContainerDetailsTokenTableComponent);
    const cmp = fx.componentInstance;

    expect(cmp.displayedColumns).toEqual(expect.arrayContaining(["actions"]));
  });

  it("sets the paginator but leaves sort unset on both internal and external data sources", () => {
    // MatTableDataSource reads _sort.sortChange/_sort.initialized whenever the table reconnects.
    // Anything that is not a MatSort there makes that a merge() over undefined, which throws and
    // leaves the data source unable to render. Ordering is done by this component, not by the
    // data source, so the seat stays empty.
    const ds = component.containerTokenData();
    expect(ds.paginator).toBe(component.paginator);
    expect(ds.sort).toBeFalsy();
    expect(component.dataSource().sort).toBeFalsy();
  });

  it("updates filterValue & sets filter on both internal and external data sources", () => {
    const mockEvent = { target: { value: " testFilter " } } as unknown as Event;
    component.handleFilterInput(mockEvent);

    expect(component.filterValue()).toBe("testFilter");
    expect(component.dataSource().filter).toBe("testfilter");
    expect(component.containerTokenData().filter).toBe("testfilter");
  });

  it("isAssignableToAllToken true when assigned user is set and at least one token is unassigned", () => {
    containerServiceMock.containerDetails.set({
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
    ] as ContainerDetailToken[];
    fixture.detectChanges();

    expect(component.isAssignableToAllToken()).toBe(true);
  });

  it("isUnassignableFromAllToken true when any token has a username", () => {
    const ds = component.containerTokenData();
    ds.data = [
      { serial: "S1", username: "", active: true },
      { serial: "S2", username: "bob", active: true }
    ] as ContainerDetailToken[];
    fixture.detectChanges();

    expect(component.isUnassignableFromAllToken()).toBe(true);
  });

  it("isUnassignableFromAllToken false when all tokens are unassigned", () => {
    const ds = component.containerTokenData();
    ds.data = [
      { serial: "S1", username: "", active: true },
      { serial: "S2", username: "", active: true }
    ] as ContainerDetailToken[];
    fixture.detectChanges();

    expect(component.isUnassignableFromAllToken()).toBe(false);
  });

  it("removeTokenFromContainer confirms and removes on confirm=true", () => {
    jest
      .spyOn(containerServiceMock, "removeTokenFromContainer")
      .mockReturnValue(of(MockPiResponse.fromValue<boolean>(true)));
    component.removeTokenFromContainer("CONT-1", "Mock serial");
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith({
      component: SimpleConfirmationDialogComponent,
      data: {
        confirmAction: { label: "Remove", type: "destruct", value: true },
        itemType: "token",
        items: ["Mock serial"],
        title: "Remove Token"
      }
    });
    confirmClosed.next(true);
    confirmClosed.complete();
    expect(containerServiceMock.removeTokenFromContainer).toHaveBeenCalledWith("CONT-1", "Mock serial");
    expect(containerServiceMock.containerDetailsResource.reload).toHaveBeenCalled();
  });

  it("removeTokenFromContainer does nothing when confirm=false", () => {
    confirmClosed.next(false);
    confirmClosed.complete();
    component.removeTokenFromContainer("CONT-1", "Mock serial");
    expect(containerServiceMock.removeTokenFromContainer).not.toHaveBeenCalled();
  });

  it("deleteTokenFromContainer confirms and deletes on confirm=true", () => {
    component.deleteTokenFromContainer("Another serial");
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith({
      component: SimpleConfirmationDialogComponent,
      data: {
        confirmAction: { label: "Delete", type: "destruct", value: true },
        itemType: "token",
        items: ["Another serial"],
        title: "Delete Token"
      }
    });
    confirmClosed.next(true);
    confirmClosed.complete();
    expect(tokenServiceMock.deleteToken).toHaveBeenCalledWith("Another serial");
    expect(containerServiceMock.containerDetailsResource.reload).toHaveBeenCalled();
  });

  it("assignUserToToken assigns the selected user and notifies success", () => {
    const notificationService = TestBed.inject(NotificationService);
    component.assignedUser.set({ user_name: "userA", user_realm: "realm1", user_resolver: "", user_id: "" });

    component.assignUserToToken({ serial: "Mock serial", active: true } as ContainerDetailToken);

    expect(tokenServiceMock.assignUser).toHaveBeenCalledWith({
      tokenSerial: "Mock serial",
      username: "userA",
      realm: "realm1"
    });
    expect(notificationService.success).toHaveBeenCalledWith("User assigned to token");
    expect(containerServiceMock.containerDetailsResource.reload).toHaveBeenCalled();
  });
});
