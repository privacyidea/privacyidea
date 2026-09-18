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
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ROUTE_PATHS } from "@app/route_paths";
import { environment } from "@env/environment";
import { AuthService } from "@services/auth/auth.service";
import { ContentService } from "@services/content/content.service";
import { NotificationService } from "@services/notification/notification.service";
import { MockAuthService, MockContentService, MockNotificationService, MockPiResponse } from "@testing/mock-services";
import { lastValueFrom, of } from "rxjs";
import { ApiClientService } from "./api-client.service";

describe("ApiClientService", () => {
  let service: ApiClientService;
  let httpMock: HttpTestingController;
  let notifyMock: MockNotificationService;
  let contentService: MockContentService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ApiClientService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService }
      ]
    });
    service = TestBed.inject(ApiClientService);
    httpMock = TestBed.inject(HttpTestingController);
    notifyMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should create a client and store the issued key once", async () => {
    const promise = service.createClient("My Client", "keycloak");

    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/`);
    expect(req.request.method).toBe("POST");
    expect(req.request.body).toEqual({ display_name: "My Client", client_type: "keycloak" });
    req.flush(
      MockPiResponse.fromValue({
        id: "abc",
        display_name: "My Client",
        client_type: "keycloak",
        key_id: "deadbeef",
        status: "active",
        created_at: "2026-01-01T00:00:00Z",
        last_used_at: null,
        api_key: "pi_deadbeef_secret"
      })
    );

    await promise;
    expect(notifyMock.success).toHaveBeenCalledWith("Successfully created API client: My Client.");
    expect(service.lastIssuedKey()).toEqual({ displayName: "My Client", apiKey: "pi_deadbeef_secret" });
  });

  it("should show error notification when creating a client fails", async () => {
    const promise = service.createClient("My Client", "keycloak");

    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notifyMock.error).toHaveBeenCalledWith("Failed to create API client. Something went wrong");
    expect(service.lastIssuedKey()).toBeNull();
  });

  it("should dismiss the issued key", async () => {
    const promise = service.rotateClient("abc", "My Client");
    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/abc/rotate`);
    req.flush(
      MockPiResponse.fromValue({
        id: "abc",
        display_name: "My Client",
        client_type: "keycloak",
        key_id: "deadbeef",
        status: "active",
        created_at: "2026-01-01T00:00:00Z",
        last_used_at: null,
        api_key: "pi_deadbeef_new_secret"
      })
    );
    await promise;
    expect(service.lastIssuedKey()).not.toBeNull();

    service.dismissIssuedKey();
    expect(service.lastIssuedKey()).toBeNull();
  });

  it("should update a client", async () => {
    const promise = service.updateClient("abc", { display_name: "Renamed", status: "suspended" });

    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/abc`);
    expect(req.request.method).toBe("PATCH");
    expect(req.request.body).toEqual({ display_name: "Renamed", status: "suspended" });
    req.flush(MockPiResponse.fromValue({}));

    await promise;
    expect(notifyMock.success).toHaveBeenCalledWith("Successfully saved API client.");
  });

  it("should show error notification when updating a client fails", async () => {
    const promise = service.updateClient("abc", { display_name: "Renamed" });

    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/abc`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notifyMock.error).toHaveBeenCalledWith("Failed to save API client. Something went wrong");
  });

  it("should show error notification when rotating a client's key fails", async () => {
    const promise = service.rotateClient("abc", "My Client");

    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/abc/rotate`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notifyMock.error).toHaveBeenCalledWith("Failed to rotate API key. Something went wrong");
    expect(service.lastIssuedKey()).toBeNull();
  });

  it("should delete a client", async () => {
    const promise = service.deleteClient("abc");

    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/abc`);
    expect(req.request.method).toBe("DELETE");
    req.flush(MockPiResponse.fromValue("abc"));

    await promise;
    expect(notifyMock.success).toHaveBeenCalledWith("Successfully deleted API client.");
  });

  it("should show error notification when deleting a client fails", async () => {
    const promise = service.deleteClient("abc");

    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/abc`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notifyMock.error).toHaveBeenCalledWith("Failed to delete API client. Something went wrong");
  });

  it("should list remembered devices for a client", async () => {
    const promise = service.getRememberedDevices("abc", { page: 2, pageSize: 10, realm: "realm1" });

    const req = httpMock.expectOne(
      (r) => r.url === `${environment.proxyUrl}/clients/abc/remembered_devices` && r.method === "GET"
    );
    expect(req.request.params.get("page")).toBe("2");
    expect(req.request.params.get("pagesize")).toBe("10");
    expect(req.request.params.get("realm")).toBe("realm1");
    req.flush(
      MockPiResponse.fromValue({
        devices: [
          {
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
          }
        ],
        count: 1,
        prev: 1,
        next: null
      })
    );

    const page = await promise;
    expect(page.count).toBe(1);
    expect(page.devices.length).toBe(1);
    expect(page.devices[0].device_id).toBe("dev1");
  });

  it("should notify and reject rather than report an empty page when listing remembered devices fails", async () => {
    const promise = service.getRememberedDevices("abc");

    const req = httpMock.expectOne(
      (r) => r.url === `${environment.proxyUrl}/clients/abc/remembered_devices` && r.method === "GET"
    );
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow("remembered-devices-load-failed");
    expect(notifyMock.error).toHaveBeenCalledWith("Failed to load remembered devices. Something went wrong");
  });

  it("should bump the remembered-devices reload trigger", () => {
    // The hook the top-bar refresh button pulls; the devices table tracks this trigger.
    expect(service.rememberedDevicesReloadTrigger()).toBe(0);
    service.reloadRememberedDevices();
    expect(service.rememberedDevicesReloadTrigger()).toBe(1);
  });

  it("should revoke a single remembered device", async () => {
    const promise = service.revokeDevice("abc", "dev1");

    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/abc/remembered_devices/dev1`);
    expect(req.request.method).toBe("DELETE");
    req.flush(MockPiResponse.fromValue("dev1"));

    await promise;
    expect(notifyMock.success).toHaveBeenCalledWith("Successfully revoked the remembered device.");
  });

  it("should show error notification when revoking a single remembered device fails", async () => {
    const promise = service.revokeDevice("abc", "dev1");

    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/abc/remembered_devices/dev1`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notifyMock.error).toHaveBeenCalledWith("Failed to revoke the remembered device. Something went wrong");
  });

  it("should revoke all remembered devices for a client with optional realm/user filters", async () => {
    const promise = service.revokeAllForClient("abc", { realm: "realm1", user: "alice" });

    const req = httpMock.expectOne(
      (request) =>
        request.url === `${environment.proxyUrl}/clients/abc/remembered_devices` &&
        request.params.get("realm") === "realm1" &&
        request.params.get("user") === "alice"
    );
    expect(req.request.method).toBe("DELETE");
    req.flush(MockPiResponse.fromValue(3));

    const count = await promise;
    expect(count).toBe(3);
  });

  it("should show error notification when revoking all remembered devices for a client fails", async () => {
    const promise = service.revokeAllForClient("abc");

    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/abc/remembered_devices`);
    req.flush(MockPiResponse.fromError({ message: "Something went wrong" }), {
      status: 400,
      statusText: "Bad Request"
    });

    await expect(promise).rejects.toThrow();
    expect(notifyMock.error).toHaveBeenCalledWith("Failed to revoke remembered devices. Something went wrong");
  });

  it("apiClientResource should not do a request and return undefined on unexpected route", () => {
    contentService.routeUrl.set(ROUTE_PATHS.EVENTS);
    const resource = service.apiClientResource.value();
    expect(resource).toBeUndefined();
    const requests = httpMock.match(() => true);
    expect(requests.length).toBe(0);
  });

  it("apiClientResource should make a request on the API clients route and populate apiClients", async () => {
    contentService.routeUrl.set(ROUTE_PATHS.POLICIES_API_CLIENTS);
    TestBed.tick();
    const req = httpMock.expectOne(`${environment.proxyUrl}/clients/`);
    expect(req.request.method).toBe("GET");
    req.flush(
      MockPiResponse.fromValue([
        {
          id: "abc",
          display_name: "My Client",
          client_type: "keycloak",
          key_id: "deadbeef",
          status: "active",
          created_at: "2026-01-01T00:00:00Z",
          last_used_at: null
        }
      ])
    );
    await lastValueFrom(of({}));

    expect(service.apiClients().length).toBe(1);
    expect(service.apiClients()[0].id).toBe("abc");
  });
});
