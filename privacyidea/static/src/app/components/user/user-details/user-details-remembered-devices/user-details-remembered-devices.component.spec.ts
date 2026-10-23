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
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ApiClientService } from "@services/api-client/api-client.service";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { UserService } from "@services/user/user.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockApiClientService, MockDialogService, MockUserService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { Subject } from "rxjs";
import { UserDetailsRememberedDevicesComponent } from "./user-details-remembered-devices.component";

describe("UserDetailsRememberedDevicesComponent", () => {
  let component: UserDetailsRememberedDevicesComponent;
  let fixture: ComponentFixture<UserDetailsRememberedDevicesComponent>;
  let apiClientServiceMock: MockApiClientService;
  let authServiceMock: MockAuthService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;

  const device = {
    device_id: "dev1",
    client_id: "client1",
    client_name: "Shibboleth",
    client_type: "privacyidea-shibboleth",
    resolver: "res1",
    user_id: "u1",
    realm: "realm1",
    user: "alice",
    ip_address: "10.0.0.1",
    user_agent: "privacyIDEA-Shibboleth",
    created_at: "2026-01-01T00:00:00Z",
    last_used_at: null,
    expires_at: "2026-02-01T00:00:00Z"
  };

  const settle = async (): Promise<void> => {
    for (let i = 0; i < 3; i++) {
      await fixture.whenStable();
      fixture.detectChanges();
    }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserDetailsRememberedDevicesComponent],
      providers: [
        { provide: ApiClientService, useClass: MockApiClientService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: UserService, useClass: MockUserService },
        { provide: Router, useValue: { navigateByUrl: jest.fn() } }
      ]
    }).compileComponents();

    apiClientServiceMock = TestBed.inject(ApiClientService) as unknown as MockApiClientService;
    apiClientServiceMock.getUserRememberedDevices = jest
      .fn()
      .mockResolvedValue({ devices: [device], count: 1, prev: null, next: null });

    const userServiceMock = TestBed.inject(UserService) as unknown as MockUserService;
    userServiceMock.detailsUser.set({ username: "alice", realm: "realm1" });
    userServiceMock.selectedUserRealm.set("realm1");

    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["remembered_device_list", "remembered_device_revoke", "api_client_list"]
    });

    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    confirmClosed = new Subject();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);

    fixture = TestBed.createComponent(UserDetailsRememberedDevicesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await settle();
  });

  it("should load the remembered devices of the shown user on all clients", () => {
    expect(apiClientServiceMock.getUserRememberedDevices).toHaveBeenCalledWith("alice", "realm1", {
      page: 1,
      pageSize: 10
    });
    expect(component.devices()).toEqual([device]);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? "";
    expect(text).toContain("Shibboleth");
  });

  it("should show the empty state when the user has no remembered devices", async () => {
    apiClientServiceMock.getUserRememberedDevices = jest
      .fn()
      .mockResolvedValue({ devices: [], count: 0, prev: null, next: null });
    apiClientServiceMock.reloadRememberedDevices();
    await settle();

    expect(component.tableState.status()).toBe("empty");
    const element = fixture.nativeElement as HTMLElement;
    expect(element.textContent).toContain("No remembered devices");
    expect(element.querySelector("table")).toBeNull();
  });

  it("should show the paginator only when there is more than one page", async () => {
    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector("mat-paginator")).toBeNull();

    apiClientServiceMock.getUserRememberedDevices = jest
      .fn()
      .mockResolvedValue({ devices: [device], count: 11, prev: null, next: 2 });
    apiClientServiceMock.reloadRememberedDevices();
    await settle();
    expect(element.querySelector("mat-paginator")).not.toBeNull();
  });

  it("should revoke a single device on its client after confirmation", async () => {
    component.revokeDevice(device);
    confirmClosed.next(true);
    confirmClosed.complete();
    await fixture.whenStable();

    expect(apiClientServiceMock.revokeDevice).toHaveBeenCalledWith("client1", "dev1");
    expect(apiClientServiceMock.reloadRememberedDevices).toHaveBeenCalled();
  });

  it("should not revoke a device when the confirmation is cancelled", () => {
    component.revokeDevice(device);
    confirmClosed.next(false);
    expect(apiClientServiceMock.revokeDevice).not.toHaveBeenCalled();
  });

  it("should revoke all devices of the user on all clients after confirmation", async () => {
    component.revokeAll();
    confirmClosed.next(true);
    confirmClosed.complete();
    await fixture.whenStable();

    expect(apiClientServiceMock.revokeAllForUser).toHaveBeenCalledWith("alice", "realm1");
  });

  it("should open the API client of a device", () => {
    const router = TestBed.inject(Router) as unknown as { navigateByUrl: jest.Mock };
    component.goToClient(device);
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_API_CLIENTS_DETAILS + "client1");
  });

  it("should load nothing without the remembered_device_list right", async () => {
    authServiceMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });
    apiClientServiceMock.getUserRememberedDevices.mockClear();
    apiClientServiceMock.reloadRememberedDevices();
    await settle();

    expect(apiClientServiceMock.getUserRememberedDevices).not.toHaveBeenCalled();
    expect(component.tableState.status()).toBe("denied");
  });
});
