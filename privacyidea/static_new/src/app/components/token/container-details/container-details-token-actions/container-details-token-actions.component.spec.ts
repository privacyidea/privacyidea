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
import { ContainerDetailsTokenActionsComponent } from "./container-details-token-actions.component";
import {
  MockContainerService,
  MockLocalService,
  MockNotificationService,
  MockTokenService
} from "../../../../../testing/mock-services";
import { AuthService } from "../../../../services/auth/auth.service";
import { ContainerService } from "../../../../services/container/container.service";
import { TokenService } from "../../../../services/token/token.service";
import { MatDialog } from "@angular/material/dialog";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import { MatTableDataSource } from "@angular/material/table";
import { signal, WritableSignal } from "@angular/core";
import { of } from "rxjs";
import { provideHttpClient } from "@angular/common/http";
import { MockAuthService } from "../../../../../testing/mock-services/mock-auth-service";
import "@angular/localize/init";

describe("ContainerDetailsTokenActionsComponent", () => {
  let component: ContainerDetailsTokenActionsComponent;
  let fixture: ComponentFixture<ContainerDetailsTokenActionsComponent>;
  let mockDialog: any;
  let mockContainerService: MockContainerService;
  let mockTokenService: MockTokenService;
  let mockAuthService: MockAuthService;

  const userSignal: WritableSignal<any> = signal({
    user_realm: "realm1",
    user_name: "alice",
    user_resolver: "resolver1",
    user_id: "id1"
  });

  const tokens = signal([
    { serial: "T1", username: "", active: false },
    { serial: "T2", username: "bob", active: true }
  ]);
  const tokenDataSignal: WritableSignal<MatTableDataSource<any>> = signal(new MatTableDataSource(tokens()));

  beforeEach(async () => {
    mockDialog = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of(true) }),
      closeAll: jest.fn()
    };
    tokenDataSignal.set(new MatTableDataSource(tokens()));

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
    mockContainerService = TestBed.inject(ContainerService) as any;
    mockTokenService = TestBed.inject(TokenService) as any;
    mockAuthService = TestBed.inject(AuthService) as any;

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
    tokenDataSignal.set(new MatTableDataSource(tokens));
    fixture.detectChanges();
    expect(component.isAssignableToAllToken()).toBe(false);
  });

  it("isAssignableToAllToken should be true if no user information is available", () => {
    const tokens = [{ serial: "T1" }];
    tokenDataSignal.set(new MatTableDataSource(tokens));
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
    tokenDataSignal.set(new MatTableDataSource(tokens));
    expect(component.isUnassignableFromAllToken()).toBe(false);
  });

  it("isUnassignableFromAllToken should be false if no user information is available", () => {
    const tokens = [{ serial: "T1" }, { serial: "T2" }];
    tokenDataSignal.set(new MatTableDataSource(tokens));
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
    tokenDataSignal.set(new MatTableDataSource(tokens));
    expect(component.anyActiveTokens()).toBe(false);
  });

  it("anyActiveTokens should be false if no active information is available", () => {
    const tokens = [{ serial: "T1" }, { serial: "T2" }];
    tokenDataSignal.set(new MatTableDataSource(tokens));
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
    tokenDataSignal.set(new MatTableDataSource(tokens));
    expect(component.anyDisabledTokens()).toBe(false);
  });

  it("anyDisabledTokens should be false if no active information is available", () => {
    const tokens = [{ serial: "T1" }, { serial: "T2" }];
    tokenDataSignal.set(new MatTableDataSource(tokens));
    expect(component.anyDisabledTokens()).toBe(false);
  });

  it("unassignFromAllToken early-returns when nothing to unassign", () => {
    const ds = component.tokenData();
    ds.data = [
      { serial: "S1", username: "", active: true },
      { serial: "S2", username: "", active: true }
    ] as any;
    jest.spyOn(mockTokenService, "unassignUserFromAll");

    component.unassignFromAllToken();
    expect(mockDialog.open).not.toHaveBeenCalled();
    expect(mockTokenService.unassignUserFromAll as any).not.toHaveBeenCalled();
  });

  it("unassignFromAllToken opens confirm and unassigns then reloads", () => {
    const ds = component.tokenData();
    ds.data = [
      { serial: "S1", username: "x", active: true },
      { serial: "S2", username: "", active: true }
    ] as any;
    jest.spyOn(mockTokenService, "unassignUserFromAll");

    component.unassignFromAllToken();
    expect(mockDialog.open).toHaveBeenCalledWith(
      ConfirmationDialogComponent,
      expect.objectContaining({
        data: expect.objectContaining({
          action: "unassign",
          serialList: ["S1"]
        })
      })
    );
    expect(mockTokenService.unassignUserFromAll as any).toHaveBeenCalledWith(["S1"]);
    expect(mockContainerService.containerDetailResource.reload).toHaveBeenCalled();
  });

  it("assignToAllToken early-returns when nothing to assign", () => {
    mockContainerService.containerDetail.set({
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
    ] as any;
    jest.spyOn(mockTokenService, "unassignUserFromAll");
    jest.spyOn(mockTokenService, "assignUserToAll");

    component.assignToAllToken();

    expect(mockTokenService.unassignUserFromAll as any).not.toHaveBeenCalled();
    expect(mockTokenService.assignUserToAll as any).not.toHaveBeenCalled();
  });

  it("assignToAllToken unassigns others, assigns all remaining, then reloads", () => {
    const ds = component.tokenData();
    ds.data = [
      { serial: "S1", username: "bob", active: true },
      { serial: "S2", username: "", active: true },
      { serial: "S3", username: "alice", active: true }
    ] as any;
    jest.spyOn(mockTokenService, "unassignUserFromAll");
    jest.spyOn(mockTokenService, "assignUserToAll");
    jest.spyOn(mockContainerService.containerDetailResource, "reload");

    component.assignToAllToken();

    expect(mockTokenService.unassignUserFromAll as any).toHaveBeenCalledWith(["S1"]);
    expect(mockTokenService.assignUserToAll as any).toHaveBeenCalledWith({
      tokenSerials: ["S1", "S2"],
      username: "alice",
      realm: "realm1"
    });
    expect(mockContainerService.containerDetailResource.reload).toHaveBeenCalled();
  });

  it("toggleAll delegates to containerService.toggleAll and reloads", () => {
    component.toggleAll("activate");
    expect(mockContainerService.toggleAll).toHaveBeenCalledWith("activate");
    expect(mockContainerService.containerDetailResource.reload).toHaveBeenCalled();
  });

  it("removeAll opens confirm and removes when confirm=true", () => {
    component.removeAll();
    expect(mockDialog.open).toHaveBeenCalledWith(
      ConfirmationDialogComponent,
      expect.objectContaining({
        data: expect.objectContaining({ action: "remove" })
      })
    );
    expect(mockContainerService.removeAll).toHaveBeenCalledWith("CONT-1");
    expect(mockContainerService.containerDetailResource.reload).toHaveBeenCalled();
  });

  it("removeAll does nothing when confirm=false", () => {
    mockDialog.open.mockReturnValueOnce({ afterClosed: () => of(false) } as any);
    component.removeAll();
    expect(mockContainerService.removeAll).not.toHaveBeenCalled();
  });

  it("deleteAllTokens opens confirm and deletes when confirm=true", () => {
    component.deleteAllTokens();
    expect(mockDialog.open).toHaveBeenCalledWith(ConfirmationDialogComponent, {
      data: {
        serialList: ["T1", "T2"],
        title: "Delete Selected Tokens",
        type: "token",
        action: "delete",
        numberOfTokens: 2
      }
    });
    expect(mockTokenService.bulkDeleteTokens).toHaveBeenCalledWith(["T1", "T2"]);
    expect(mockContainerService.containerDetailResource.reload).toHaveBeenCalled();
  });

  it("deleteAllTokens does NOT delete when confirm=false", () => {
    mockDialog.open.mockReturnValueOnce({ afterClosed: () => of(false) } as any);
    component.deleteAllTokens();
    expect(mockTokenService.bulkDeleteTokens).not.toHaveBeenCalled();
  });
});
