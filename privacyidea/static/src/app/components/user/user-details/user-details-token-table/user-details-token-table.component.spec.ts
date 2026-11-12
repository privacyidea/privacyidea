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
import { of, throwError } from "rxjs";

import {
  MockContainerService,
  MockContentService,
  MockDialogService,
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
import { ContainerService, ContainerDetailToken } from "@services/container/container.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MatTableDataSource } from "@angular/material/table";
import { TokenDetails, Tokens, TokenService } from "@services/token/token.service";
import { UserService } from "@services/user/user.service";

import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { expectsTableStateGating } from "@testing/table-state-gating";
import { MockPiResponse } from "@testing/mock-services/mock-utils";

describe("UserDetailsTokenTableComponent", () => {
  let fixture: ComponentFixture<UserDetailsTokenTableComponent>;
  let component: UserDetailsTokenTableComponent;

  let tokenServiceMock: MockTokenService;
  let notificationServiceMock: MockNotificationService;
  let containerServiceMock: MockContainerService;
  let dialogServiceMock: MockDialogService;

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
        { provide: ContainerService, useClass: MockContainerService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: UserService, useClass: MockUserService },
        { provide: NotificationService, useClass: MockNotificationService },
        MockLocalService
      ]
    }).compileComponents();

    tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    containerServiceMock = TestBed.inject(ContainerService) as unknown as MockContainerService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;

    fixture = TestBed.createComponent(UserDetailsTokenTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => jest.clearAllMocks());

  it("names only the routes out of the empty list that this admin is allowed to take", () => {
    const authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    // Rights drive the computed; tokenEnrollmentAllowed is a plain stub and reads no signal, so the
    // rights change is what makes the hint re-evaluate after it is set.
    const withRights = (canEnroll: boolean, rights: string[]) => {
      authServiceMock.tokenEnrollmentAllowed.mockReturnValue(canEnroll);
      authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights });
    };

    withRights(true, ["assign"]);
    expect(component.emptyHint()).toContain("or assign an existing one");

    withRights(true, []);
    expect(component.emptyHint()).toBe("Enroll a new token for this user.");

    withRights(false, ["assign"]);
    expect(component.emptyHint()).toBe("Assign an existing token to this user.");

    withRights(false, []);
    expect(component.emptyHint()).toBe("");
  });

  it("gates the table on its read right, row count and filter", () => {
    expectsTableStateGating({
      state: component.tableState,
      right: "tokenlist"
    });
  });

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

  it("leaves the data source's sort unset so it keeps a working change subscription", () => {
    // MatTableDataSource reads _sort.sortChange/_sort.initialized whenever the table reconnects.
    // Anything that is not a MatSort there makes that a merge() over undefined, which throws and
    // leaves the data source unable to render. Ordering is done by this component, not by the
    // data source, so the seat stays empty.
    expect(component.dataSource.sort).toBeFalsy();
  });

  it("renders rows after the table returns from the empty state", () => {
    // The table is torn down when the list empties and built again when rows come back. On the way
    // back its data source reconnects, which is where anything left in the data source's sort seat
    // would throw and leave the table unable to render.
    const authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authServiceMock.authData.set({ ...authServiceMock.authData()!, rights: ["tokenlist"] });

    const table = () => fixture.nativeElement.querySelector("table");
    const respondWith = (...tokens: TokenDetails[]) => {
      tokenServiceMock.userTokenResource.value.set(
        MockPiResponse.fromValue<Tokens>({ count: tokens.length, current: tokens.length, tokens })
      );
      fixture.detectChanges();
    };

    respondWith({
      serial: "T-FIRST",
      tokentype: "hotp",
      active: true,
      revoked: false,
      locked: false,
      description: "",
      failcount: 0,
      maxfail: 10,
      container_serial: "",
      user_realm: "r1",
      username: "alice",
      resolver: ""
    } as TokenDetails);
    expect(component.tableState.status()).toBe("ready");
    expect(table()).not.toBeNull();

    // Unassigning the last token empties the list and takes the table away.
    respondWith();
    expect(component.tableState.status()).toBe("empty");
    expect(table()).toBeNull();

    respondWith({
      serial: "T-AFTER-ASSIGN",
      tokentype: "hotp",
      active: true,
      revoked: false,
      locked: false,
      description: "",
      failcount: 0,
      maxfail: 10,
      container_serial: "",
      user_realm: "r1",
      username: "alice",
      resolver: ""
    } as TokenDetails);

    expect(table()).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain("T-AFTER-ASSIGN");
  });

  const showTokens = (...rows: ContainerDetailToken[]) => {
    component.userTokenData.set(new MatTableDataSource(rows as unknown as TokenDetails[]));
    fixture.detectChanges();
  };

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

  it("keeps the previous list in userTokenData while the resource has no value (linkedSignal fallback)", () => {
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

    expect(component.userTokenData().data.map((t: TokenDetails) => t.serial)).toEqual(["KEEP-ME"]);
    expect(component.dataSource.data).toEqual([]);
  });

  it("falls back to a new empty data source when there is no resource value and no previous value", () => {
    tokenServiceMock.userTokenResource.value.set(undefined);

    const freshFixture = TestBed.createComponent(UserDetailsTokenTableComponent);
    freshFixture.detectChanges();

    expect(freshFixture.componentInstance.dataSource.data).toEqual([]);
  });

  it("falls back to an empty tokens array when the resource value has no tokens", () => {
    tokenServiceMock.userTokenResource.value.set(
      MockPiResponse.fromValue<Tokens>({ count: 0, current: 0 } as unknown as Tokens)
    );

    fixture.detectChanges();

    expect(component.dataSource.data).toEqual([]);
  });

  it("scopes the selection to the rows of the token table", () => {
    showTokens({ serial: "A" } as unknown as ContainerDetailToken, { serial: "B" } as unknown as ContainerDetailToken);

    component.selector.selectAllRows();

    expect(component.selector.selectedRows().map((row) => row.serial)).toEqual(["A", "B"]);
    expect(component.selector.allRowsSelected()).toBe(true);
  });

  it("deleteSelected calls bulkDeleteWithConfirmDialog with the selected serials", () => {
    const rowA = { serial: "A" } as unknown as ContainerDetailToken;
    const rowB = { serial: "B" } as unknown as ContainerDetailToken;
    showTokens(rowA, rowB);
    component.selector.selectAllRows();

    component.deleteSelected();

    expect(tokenServiceMock.bulkDeleteWithConfirmDialog).toHaveBeenCalledWith(["A", "B"], expect.any(Function));
    const afterDelete = (tokenServiceMock.bulkDeleteWithConfirmDialog as jest.Mock).mock.calls[0][1];
    afterDelete();
    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
  });

  it("unassignSelected unassigns each selected token and reloads", () => {
    const rowA = { serial: "A" } as unknown as ContainerDetailToken;
    const rowB = { serial: "B" } as unknown as ContainerDetailToken;
    showTokens(rowA, rowB);
    component.selector.selectAllRows();

    component.unassignSelected();

    expect(tokenServiceMock.unassignUser).toHaveBeenCalledWith("A", false);
    expect(tokenServiceMock.unassignUser).toHaveBeenCalledWith("B", false);
    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
    expect(notificationServiceMock.error).not.toHaveBeenCalled();
  });

  it("unassignSelected still reloads when one of the requests fails and shows a summary", () => {
    const rowA = { serial: "A" } as unknown as ContainerDetailToken;
    const rowB = { serial: "B" } as unknown as ContainerDetailToken;
    showTokens(rowA, rowB);
    component.selector.selectAllRows();
    tokenServiceMock.unassignUser.mockImplementation((serial: string) =>
      serial === "A" ? throwError(() => new Error("failed")) : of(null)
    );

    component.unassignSelected();

    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
    expect(notificationServiceMock.error).toHaveBeenCalledWith("1/2 unassign failed: A");
  });

  it("toggleActiveSelected toggles each selected token and reloads", () => {
    const rowA = { serial: "A", active: true } as unknown as ContainerDetailToken;
    const rowB = { serial: "B", active: false } as unknown as ContainerDetailToken;
    showTokens(rowA, rowB);
    component.selector.selectAllRows();

    component.toggleActiveSelected();

    expect(tokenServiceMock.toggleActive).toHaveBeenCalledWith("A", true, false);
    expect(tokenServiceMock.toggleActive).toHaveBeenCalledWith("B", false, false);
    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
    expect(notificationServiceMock.error).not.toHaveBeenCalled();
  });

  it("toggleActiveSelected still reloads when one of the requests fails and shows a summary", () => {
    const rowA = { serial: "A", active: true } as unknown as ContainerDetailToken;
    const rowB = { serial: "B", active: false } as unknown as ContainerDetailToken;
    showTokens(rowA, rowB);
    component.selector.selectAllRows();
    tokenServiceMock.toggleActive.mockImplementation((serial: string) =>
      serial === "A" ? throwError(() => new Error("failed")) : of(null)
    );

    component.toggleActiveSelected();

    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
    expect(notificationServiceMock.error).toHaveBeenCalledWith("1/2 toggle active failed: A");
  });

  it("resetFailcountSelected resets each selected token and reloads", () => {
    const rowA = { serial: "A" } as unknown as ContainerDetailToken;
    const rowB = { serial: "B" } as unknown as ContainerDetailToken;
    showTokens(rowA, rowB);
    component.selector.selectAllRows();

    component.resetFailcountSelected();

    expect(tokenServiceMock.resetFailCount).toHaveBeenCalledWith("A", false);
    expect(tokenServiceMock.resetFailCount).toHaveBeenCalledWith("B", false);
    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
    expect(notificationServiceMock.error).not.toHaveBeenCalled();
  });

  it("resetFailcountSelected still reloads when one of the requests fails and shows a summary", () => {
    const rowA = { serial: "A" } as unknown as ContainerDetailToken;
    const rowB = { serial: "B" } as unknown as ContainerDetailToken;
    showTokens(rowA, rowB);
    component.selector.selectAllRows();
    tokenServiceMock.resetFailCount.mockImplementation((serial: string) =>
      serial === "A" ? throwError(() => new Error("failed")) : of(null)
    );

    component.resetFailcountSelected();

    expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
    expect(notificationServiceMock.error).toHaveBeenCalledWith("1/2 reset fail count failed: A");
  });

  describe("addToContainerSelected", () => {
    const owner = { username: "otheruser", realm: "otherrealm" };
    const assignedArgs = { containerSerial: "CONT-001", username: "testuser", userRealm: "defrealm" };

    const arrange = (
      dialogResult: { containerSerial: string; assignToUser: boolean; previousOwner: typeof owner | null } | undefined,
      serials: string[],
      backend?: Record<string, boolean>
    ) => {
      dialogServiceMock.openDialogAsync.mockResolvedValue(dialogResult);
      showTokens(...serials.map((serial) => ({ serial }) as unknown as ContainerDetailToken));
      component.selector.selectAllRows();
      const userServiceMock = TestBed.inject(UserService) as unknown as MockUserService;
      userServiceMock.detailsUser.set({ username: "testuser", realm: "defrealm" });
      userServiceMock.selectedUserRealm.set("defrealm");
      if (backend) {
        containerServiceMock.addTokensToContainer.mockReturnValue(of(MockPiResponse.fromValue(backend)));
      }
    };
    const dialogResult = (assignToUser: boolean, previousOwner: typeof owner | null = null) => ({
      containerSerial: "CONT-001",
      assignToUser,
      previousOwner
    });

    it("sends all selected tokens in one request, reloads and leaves the container owner alone", async () => {
      arrange(dialogResult(false), ["A", "B"], { A: true, B: true });

      await component.addToContainerSelected();

      expect(containerServiceMock.addTokensToContainer).toHaveBeenCalledTimes(1);
      expect(containerServiceMock.addTokensToContainer).toHaveBeenCalledWith("CONT-001", ["A", "B"], false);
      expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
      expect(notificationServiceMock.error).not.toHaveBeenCalled();
      expect(containerServiceMock.assignUser).not.toHaveBeenCalled();
    });

    it("reports the tokens the backend refused", async () => {
      arrange(dialogResult(false), ["A", "B"], { A: false, B: true });

      await component.addToContainerSelected();

      expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalledTimes(1);
      expect(notificationServiceMock.error).toHaveBeenCalledWith("1/2 add to container failed: A");
    });

    it("reports every token once when the request itself fails", async () => {
      arrange(dialogResult(false), ["A", "B"]);
      containerServiceMock.addTokensToContainer.mockReturnValue(throwError(() => new Error("failed")));

      await component.addToContainerSelected();

      expect(notificationServiceMock.error).toHaveBeenCalledTimes(1);
      expect(notificationServiceMock.error).toHaveBeenCalledWith("2/2 add to container failed: A, B");
    });

    it("assigns the container to the user when the dialog asked for it", async () => {
      arrange(dialogResult(true), ["A"], { A: true });

      await component.addToContainerSelected();

      expect(containerServiceMock.unassignUser).not.toHaveBeenCalled();
      expect(containerServiceMock.assignUser).toHaveBeenCalledWith(assignedArgs);
      expect(containerServiceMock.userContainersResource.reload).toHaveBeenCalled();
    });

    it("frees the container from its old owner before assigning it", async () => {
      arrange(dialogResult(true, owner), ["A"], { A: true });

      await component.addToContainerSelected();

      expect(containerServiceMock.unassignUser).toHaveBeenCalledWith("CONT-001", "otheruser", "otherrealm");
      expect(containerServiceMock.assignUser).toHaveBeenCalledWith(assignedArgs);
      expect(containerServiceMock.unassignUser.mock.invocationCallOrder[0]).toBeLessThan(
        containerServiceMock.assignUser.mock.invocationCallOrder[0]
      );
    });

    it("neither unassigns nor assigns when no token was added", async () => {
      arrange(dialogResult(true, owner), ["A", "B"], { A: false, B: false });

      await component.addToContainerSelected();

      expect(containerServiceMock.unassignUser).not.toHaveBeenCalled();
      expect(containerServiceMock.assignUser).not.toHaveBeenCalled();
      expect(notificationServiceMock.error).toHaveBeenCalledWith("2/2 add to container failed: A, B");
    });

    it.each([
      { step: "unassigning the old owner", previousOwner: owner, failing: "unassignUser" as const },
      { step: "assigning the container", previousOwner: null, failing: "assignUser" as const }
    ])(
      "reloads the user containers without its own error notification when $step fails",
      async ({ previousOwner, failing }) => {
        arrange(dialogResult(true, previousOwner), ["A"], { A: true });
        containerServiceMock[failing].mockReturnValue(throwError(() => new Error("failed")));
        containerServiceMock.userContainersResource.reload.mockClear();

        await expect(component.addToContainerSelected()).resolves.toBeUndefined();

        expect(notificationServiceMock.error).not.toHaveBeenCalled();
        expect(containerServiceMock.userContainersResource.reload).toHaveBeenCalled();
      }
    );

    it("does nothing when the dialog is cancelled", async () => {
      arrange(undefined, ["A"]);

      await component.addToContainerSelected();

      expect(containerServiceMock.addTokensToContainer).not.toHaveBeenCalled();
      expect(tokenServiceMock.userTokenResource.reload).not.toHaveBeenCalled();
    });
  });

  describe("active and fail counter cells", () => {
    const cell = (column: string): HTMLElement => fixture.nativeElement.querySelector(`td.mat-column-${column}`);
    const showsTokenWithRights = (rights: string[]): void => {
      const authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
      authServiceMock.authData.set({ ...authServiceMock.authData()!, rights: ["tokenlist", ...rights] });
      const tableUtils = TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;
      tableUtils.getDisplayText.mockImplementation((columnKey: string) => `${columnKey} value`);
      tokenServiceMock.userTokenResource.value.set(
        MockPiResponse.fromValue<Tokens>({
          count: 1,
          current: 1,
          tokens: [{ serial: "T-1", active: true, failcount: 3, maxfail: 10 } as TokenDetails]
        })
      );
      fixture.detectChanges();
    };

    const tableUtils = (): MockTableUtilsService =>
      TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;

    it("offers the toggle and the reset as buttons when the token may be toggled and with the reset right", () => {
      tableUtils().canToggleActive.mockReturnValue(true);
      showsTokenWithRights(["reset"]);

      expect(cell("active").querySelector("button")?.textContent).toContain("active value");
      expect(cell("failcount").querySelector('[role="button"]')?.textContent).toContain("failcount value");
    });

    it("shows the active state and the fail counter read-only otherwise", () => {
      showsTokenWithRights([]);

      expect(cell("active").textContent).toContain("active value");
      expect(cell("failcount").textContent).toContain("failcount value");
      expect(cell("active").querySelector("button")).toBeNull();
      expect(cell("failcount").querySelector('[role="button"]')).toBeNull();
    });

    it.each([["enable"], ["disable"]])("offers (de)activating the selection with only the %s right", (right) => {
      const bulkToggle = (): HTMLButtonElement | undefined =>
        Array.from<HTMLButtonElement>(fixture.nativeElement.querySelectorAll("button")).find((button) =>
          button.textContent?.includes("(De)activate")
        );
      showsTokenWithRights([]);
      expect(bulkToggle()).toBeUndefined();

      showsTokenWithRights([right]);
      expect(bulkToggle()).toBeDefined();
    });

    it("reloads the user's tokens once the active state was toggled", () => {
      tableUtils().canToggleActive.mockReturnValue(true);
      showsTokenWithRights([]);

      cell("active").querySelector("button")!.click();

      expect(tokenServiceMock.toggleActive).toHaveBeenCalledWith("T-1", true);
      expect(tokenServiceMock.userTokenResource.reload).toHaveBeenCalled();
    });
  });
});
