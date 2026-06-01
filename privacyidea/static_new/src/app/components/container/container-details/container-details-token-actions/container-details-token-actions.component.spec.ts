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
import { signal, WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatDialog } from "@angular/material/dialog";
import { MatTableDataSource } from "@angular/material/table";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { AuthService } from "@services/auth/auth.service";
import { ContainerDetailToken, ContainerService } from "@services/container/container.service";
import { TokenService } from "@services/token/token.service";
import {
  MockContainerService,
  MockLocalService,
  MockNotificationService,
  MockTokenService
} from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { of } from "rxjs";
import { ContainerDetailsTokenActionsComponent } from "./container-details-token-actions.component";

describe("ContainerDetailsTokenActionsComponent", () => {
  let component: ContainerDetailsTokenActionsComponent;
  let fixture: ComponentFixture<ContainerDetailsTokenActionsComponent>;
  let mockDialog: { open: jest.Mock; closeAll: jest.Mock };
  let mockContainerService: MockContainerService;
  let mockTokenService: MockTokenService;

  const userSignal: WritableSignal<{
    user_realm: string;
    user_name: string;
    user_resolver: string;
    user_id: string;
  }> = signal({
    user_realm: "realm1",
    user_name: "alice",
    user_resolver: "resolver1",
    user_id: "id1"
  });

  const tokens = signal<Partial<ContainerDetailToken>[]>([
    { serial: "T1", username: "", active: false },
    { serial: "T2", username: "bob", active: true }
  ]);
  const tokenDataSignal: WritableSignal<MatTableDataSource<ContainerDetailToken>> = signal(
    new MatTableDataSource(tokens() as ContainerDetailToken[])
  );

  beforeEach(async () => {
    mockDialog = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of({ confirmed: true }) }),
      closeAll: jest.fn()
    };
    tokenDataSignal.set(new MatTableDataSource(tokens() as ContainerDetailToken[]));

    await TestBed.configureTestingModule({
      imports: [ContainerDetailsTokenActionsComponent],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: MatDialog, useValue: mockDialog },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsTokenActionsComponent);
    component = fixture.componentInstance;
    mockContainerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;

    component.containerSerial = "CONT-1";
    component.user = userSignal;
    component.tokenData = tokenDataSignal;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("isAssignableToAllToken should be true if any token has no user", () => {
    expect(component.isAssignableToAllToken()).toBe(true);
  });

  it("isAssignableToAllToken should be false if all tokens have a user", () => {
    const tokens = [{ serial: "T1", username: "alice", active: false }];
    tokenDataSignal.set(new MatTableDataSource(tokens as unknown as ContainerDetailToken[]));
    fixture.detectChanges();
    expect(component.isAssignableToAllToken()).toBe(false);
  });

  it("isAssignableToAllToken should be true if no user information is available", () => {
    const tokens = [{ serial: "T1" }];
    tokenDataSignal.set(new MatTableDataSource(tokens as unknown as ContainerDetailToken[]));
    fixture.detectChanges();
    expect(component.isAssignableToAllToken()).toBe(true);
  });

  it("isUnassignableFromAllToken should be true if any token has a user", () => {
    expect(component.isUnassignableFromAllToken()).toBe(true);
  });

  it("isUnassignableFromAllToken should be false if no token has a user", () => {
    const tokens = [
      { serial: "T1", username: "", active: false },
      { serial: "T2", username: "", active: false }
    ];
    tokenDataSignal.set(new MatTableDataSource(tokens as unknown as ContainerDetailToken[]));
    expect(component.isUnassignableFromAllToken()).toBe(false);
  });

  it("isUnassignableFromAllToken should be false if no user information is available", () => {
    const tokens = [{ serial: "T1" }, { serial: "T2" }];
    tokenDataSignal.set(new MatTableDataSource(tokens as unknown as ContainerDetailToken[]));
    expect(component.isUnassignableFromAllToken()).toBe(false);
  });

  it("anyActiveTokens should be true if any token is active", () => {
    expect(component.anyActiveTokens()).toBe(true);
  });

  it("anyActiveTokens should be false if no token is active", () => {
    const tokens = [
      { serial: "T1", username: "", active: false },
      { serial: "T2", username: "", active: false }
    ];
    tokenDataSignal.set(new MatTableDataSource(tokens as unknown as ContainerDetailToken[]));
    expect(component.anyActiveTokens()).toBe(false);
  });

  it("anyActiveTokens should be false if no active information is available", () => {
    const tokens = [{ serial: "T1" }, { serial: "T2" }];
    tokenDataSignal.set(new MatTableDataSource(tokens as unknown as ContainerDetailToken[]));
    expect(component.anyActiveTokens()).toBe(false);
  });

  it("anyDisabledTokens should be true if any token is not active", () => {
    expect(component.anyDisabledTokens()).toBe(true);
  });

  it("anyDisabledTokens should be false if no token is disabled", () => {
    const tokens = [
      { serial: "T1", username: "", active: true },
      { serial: "T2", username: "", active: true }
    ];
    tokenDataSignal.set(new MatTableDataSource(tokens as unknown as ContainerDetailToken[]));
    expect(component.anyDisabledTokens()).toBe(false);
  });

  it("anyDisabledTokens should be false if no active information is available", () => {
    const tokens = [{ serial: "T1" }, { serial: "T2" }];
    tokenDataSignal.set(new MatTableDataSource(tokens as unknown as ContainerDetailToken[]));
    expect(component.anyDisabledTokens()).toBe(false);
  });

  it("unassignFromAllToken early-returns when nothing to unassign", () => {
    const ds = component.tokenData();
    ds.data = [
      { serial: "S1", username: "", active: true },
      { serial: "S2", username: "", active: true }
    ] as ContainerDetailToken[];
    jest.spyOn(mockTokenService, "unassignUserFromAll");

    component.unassignFromAllToken();
    expect(mockDialog.open).not.toHaveBeenCalled();
    expect(mockTokenService.unassignUserFromAll).not.toHaveBeenCalled();
  });

  it("unassignFromAllToken opens confirm and unassigns then reloads", () => {
    const ds = component.tokenData();
    ds.data = [
      { serial: "S1", username: "x", active: true },
      { serial: "S2", username: "", active: true }
    ] as ContainerDetailToken[];
    jest.spyOn(mockTokenService, "unassignUserFromAll");

    component.unassignFromAllToken();
    expect(mockDialog.open).toHaveBeenCalledWith(
      SimpleConfirmationDialogComponent,
      expect.objectContaining({
        data: {
          confirmAction: { label: "Unassign", type: "destruct", value: true },
          itemType: "token",
          items: ["S1"],
          title: "Unassign User from All Tokens"
        },
        disableClose: false,
        hasBackdrop: true
      })
    );
    expect(mockTokenService.unassignUserFromAll).toHaveBeenCalledWith(["S1"]);
    expect(mockContainerService.containerDetailsResource.reload).toHaveBeenCalled();
  });

  it("assignToAllToken early-returns when nothing to assign", () => {
    mockContainerService.containerDetails.set({
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
    const ds = component.tokenData();
    ds.data = [
      { serial: "S1", username: "alice", active: true },
      { serial: "S2", username: "alice", active: true }
    ] as ContainerDetailToken[];
    jest.spyOn(mockTokenService, "unassignUserFromAll");
    jest.spyOn(mockTokenService, "assignUserToAll");

    component.assignToAllToken();

    expect(mockTokenService.unassignUserFromAll).not.toHaveBeenCalled();
    expect(mockTokenService.assignUserToAll).not.toHaveBeenCalled();
  });

  it("assignToAllToken unassigns others, assigns all remaining, then reloads", () => {
    const ds = component.tokenData();
    ds.data = [
      { serial: "S1", username: "bob", active: true },
      { serial: "S2", username: "", active: true },
      { serial: "S3", username: "alice", active: true }
    ] as ContainerDetailToken[];
    jest.spyOn(mockTokenService, "unassignUserFromAll");
    jest.spyOn(mockTokenService, "assignUserToAll");
    jest.spyOn(mockContainerService.containerDetailsResource, "reload");

    component.assignToAllToken();

    expect(mockTokenService.unassignUserFromAll).toHaveBeenCalledWith(["S1"]);
    expect(mockTokenService.assignUserToAll).toHaveBeenCalledWith({
      tokenSerials: ["S1", "S2"],
      username: "alice",
      realm: "realm1"
    });
    expect(mockContainerService.containerDetailsResource.reload).toHaveBeenCalled();
  });

  it("toggleAll delegates to containerService.toggleAll and reloads", () => {
    component.toggleAll("activate");
    expect(mockContainerService.toggleAll).toHaveBeenCalledWith("activate");
    expect(mockContainerService.containerDetailsResource.reload).toHaveBeenCalled();
  });

  it("removeAll opens confirm and removes when confirm=true", () => {
    component.removeAll();
    expect(mockDialog.open).toHaveBeenCalledWith(
      SimpleConfirmationDialogComponent,
      expect.objectContaining({
        data: {
          confirmAction: { label: "Remove", type: "destruct", value: true },
          itemType: "token",
          items: ["T1", "T2"],
          title: "Remove Token"
        },
        disableClose: false,
        hasBackdrop: true
      })
    );
    expect(mockContainerService.removeAll).toHaveBeenCalledWith("CONT-1");
    expect(mockContainerService.containerDetailsResource.reload).toHaveBeenCalled();
  });

  it("removeAll does nothing when confirm=false", () => {
    mockDialog.open.mockReturnValueOnce({ afterClosed: () => of(false) });
    component.removeAll();
    expect(mockContainerService.removeAll).not.toHaveBeenCalled();
  });

  it("deleteAllTokens opens confirm and deletes when confirm=true", () => {
    const token1: ContainerDetailToken = {
      serial: "T1",
      username: "",
      active: false,
      container_serial: "",
      count: 0,
      count_window: 0,
      description: "",
      failcount: 0,
      id: 0,
      revoked: false,
      sync_window: 0,
      tokengroup: [],
      tokentype: "",
      user_editable: false,
      user_id: "",
      user_realm: ""
    };
    const token2: ContainerDetailToken = { ...token1, serial: "T2" };
    const data = new MatTableDataSource<ContainerDetailToken>([token1, token2]);
    component.tokenData.set(data);
    component.deleteAllTokens();

    expect(mockTokenService.bulkDeleteWithConfirmDialog).toHaveBeenCalledWith(["T1", "T2"], expect.any(Function));
  });

  it("deleteAllTokens does NOT delete when confirm=false", () => {
    mockDialog.open.mockReturnValueOnce({ afterClosed: () => of(false) });
    component.deleteAllTokens();
    expect(mockTokenService.bulkDeleteTokens).not.toHaveBeenCalled();
  });
});
