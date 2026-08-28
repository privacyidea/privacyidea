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
import { ApiClientService } from "@services/api-client/api-client.service";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { RealmService } from "@services/realm/realm.service";
import { MockApiClientService, MockContentService, MockDialogService, MockRealmService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { Subject } from "rxjs";
import { ApiClientRememberedDevicesComponent } from "./api-client-remembered-devices.component";

describe("ApiClientRememberedDevicesComponent", () => {
  let component: ApiClientRememberedDevicesComponent;
  let fixture: ComponentFixture<ApiClientRememberedDevicesComponent>;
  let apiClientServiceMock: MockApiClientService;
  let realmServiceMock: MockRealmService;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<boolean>;

  const device1 = {
    device_id: "dev1",
    resolver: "res1",
    user_id: "u1",
    realm: "realm1",
    user: "alice",
    ip_address: "10.0.0.1",
    user_agent: "ua",
    created_at: "2026-01-01T00:00:00Z",
    last_used_at: null,
    expires_at: "2026-02-01T00:00:00Z"
  };
  const device2 = {
    device_id: "dev2",
    resolver: "res1",
    user_id: "u2",
    realm: "realm2",
    user: null,
    ip_address: null,
    user_agent: null,
    created_at: "2026-01-02T00:00:00Z",
    last_used_at: null,
    expires_at: "2026-02-02T00:00:00Z"
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ApiClientRememberedDevicesComponent],
      providers: [
        { provide: ApiClientService, useClass: MockApiClientService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: RealmService, useClass: MockRealmService }
      ]
    }).compileComponents();

    apiClientServiceMock = TestBed.inject(ApiClientService) as unknown as MockApiClientService;
    apiClientServiceMock.getRememberedDevices = jest
      .fn()
      .mockResolvedValue({ devices: [device1, device2], count: 2, prev: null, next: null });

    realmServiceMock = TestBed.inject(RealmService) as unknown as MockRealmService;
    realmServiceMock.realmOptions.set(["realm1", "realm2"]);

    const authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authServiceMock.authData.set({
      ...MockAuthService.MOCK_AUTH_DATA,
      rights: ["remembered_device_list", "remembered_device_revoke"]
    });

    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    confirmClosed = new Subject();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);

    fixture = TestBed.createComponent(ApiClientRememberedDevicesComponent);
    fixture.componentRef.setInput("clientId", "client1");
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it("should create and load the client's remembered devices", () => {
    expect(component).toBeTruthy();
    expect(apiClientServiceMock.getRememberedDevices).toHaveBeenCalledWith("client1", {
      page: 1,
      pageSize: 50,
      realm: undefined
    });
    expect(component.devices().length).toBe(2);
    expect(component.count()).toBe(2);
  });

  it("should list the realms from the realm service", () => {
    expect(component.realmOptions()).toEqual(["realm1", "realm2"]);
  });

  it("should reload with the selected realm and reset to the first page", async () => {
    component.pageIndex.set(2);
    component.onRealmFilterChange("realm1");
    expect(component.pageIndex()).toBe(0);
    await fixture.whenStable();
    expect(apiClientServiceMock.getRememberedDevices).toHaveBeenCalledWith("client1", {
      page: 1,
      pageSize: 50,
      realm: "realm1"
    });
  });

  it("should reload the requested page on a paginator event", async () => {
    component.onPage({ pageIndex: 1, pageSize: 10, length: 2 });
    await fixture.whenStable();
    expect(apiClientServiceMock.getRememberedDevices).toHaveBeenCalledWith("client1", {
      page: 2,
      pageSize: 10,
      realm: undefined
    });
  });

  it("should revoke a single device after confirmation and reload", async () => {
    component.revokeDevice(device1);
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next(true);
    confirmClosed.complete();
    await fixture.whenStable();
    expect(apiClientServiceMock.revokeDevice).toHaveBeenCalledWith("client1", "dev1");
    expect(apiClientServiceMock.getRememberedDevices).toHaveBeenCalledTimes(2);
  });

  it("should not revoke a device when the confirmation is cancelled", () => {
    component.revokeDevice(device1);
    confirmClosed.next(false);
    confirmClosed.complete();
    expect(apiClientServiceMock.revokeDevice).not.toHaveBeenCalled();
  });

  it("should revoke all devices for a user across all clients", async () => {
    component.revokeAllForUser(device1);
    confirmClosed.next(true);
    confirmClosed.complete();
    await fixture.whenStable();
    expect(apiClientServiceMock.revokeAllInRealmAcrossClients).toHaveBeenCalledWith("realm1", "alice");
  });

  it("should do nothing when revoking all for a user without a resolved account", () => {
    component.revokeAllForUser(device2);
    expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
  });

  it("should revoke all remembered devices for the client when no realm is selected", async () => {
    expect(component.revokeAllLabel()).toBe("Revoke all");
    component.revokeAll();
    confirmClosed.next(true);
    confirmClosed.complete();
    await fixture.whenStable();
    expect(apiClientServiceMock.revokeAllForClient).toHaveBeenCalledWith("client1");
    expect(apiClientServiceMock.revokeAllInRealmAcrossClients).not.toHaveBeenCalled();
  });

  it("should do nothing when revoking all with no devices", () => {
    component.count.set(0);
    component.revokeAll();
    expect(dialogServiceMock.openDialog).not.toHaveBeenCalled();
  });

  it("should revoke all devices in the selected realm across all clients", async () => {
    component.realmFilter.set("realm1");
    expect(component.revokeAllLabel()).toBe("Revoke all in this realm");
    component.revokeAll();
    confirmClosed.next(true);
    confirmClosed.complete();
    await fixture.whenStable();
    expect(apiClientServiceMock.revokeAllInRealmAcrossClients).toHaveBeenCalledWith("realm1");
    expect(apiClientServiceMock.revokeAllForClient).not.toHaveBeenCalled();
  });

  it("should navigate to the resolved user's details", () => {
    const contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    component.goToUser(device1);
    expect(contentService.userSelected).toHaveBeenCalledWith("alice", "realm1");
  });

  it("should do nothing when the account no longer resolves", () => {
    const contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    component.goToUser(device2);
    expect(contentService.userSelected).not.toHaveBeenCalled();
  });
});
