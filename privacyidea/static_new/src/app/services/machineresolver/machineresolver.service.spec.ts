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
import { TestBed } from "@angular/core/testing";
import { Machineresolver, MachineresolverService, Machineresolvers } from "./machineresolver.service";
import { AuthService } from "../auth/auth.service";
import { ContentService } from "../content/content.service";
import { NotificationService } from "../notification/notification.service";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { provideHttpClient } from "@angular/common/http";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";
import { MockContentService, MockNotificationService, MockPiResponse } from "../../../testing/mock-services";
describe("MachineresolverService", () => {
  let service: MachineresolverService;
  let httpMock: HttpTestingController;
  let authServiceMock: MockAuthService;
  let contentServiceMock: MockContentService;
  let notificationServiceMock: MockNotificationService;
  let testMachineresolver: Machineresolver = {
    resolvername: "test-resolver",
    type: "hosts",
    data: {
      resolver: "test-resolver",
      type: "hosts"
    }
  };
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        MachineresolverService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    }).compileComponents();
    service = TestBed.inject(MachineresolverService);
    httpMock = TestBed.inject(HttpTestingController);
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
  });
  afterEach(() => {
    httpMock.verify();
    jest.clearAllMocks();
  });
  it("should be created", () => {
    expect(service).toBeTruthy();
  });
  describe("machineresolversResource", () => {
    it("should not make an HTTP request and notify if mresolverread is not allowed", () => {
      authServiceMock.actionAllowed.mockImplementation((arg) => (arg === "mresolverread" ? true : false));
      // Access the signal to trigger its computation
      service.machineresolverResource.value();
      httpMock.expectNone(`${service.machineresolverBaseUrl}`);
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        "You are not allowed to read machineresolvers."
      );
    });
    it("should make an HTTP GET request and return transformed data on success", async () => {
      authServiceMock.actionAllowed.mockImplementation((arg) => (arg === "mresolverread" ? true : false));
      authServiceMock.getHeaders.mockReturnValue({ Authorization: "test-token" });
      const mockResponse = MockPiResponse.fromValue<Machineresolvers>({
        resolver1: { resolvername: "resolver1", type: "hosts", data: { resolver: "resolver1", type: "hosts" } },
        resolver2: { resolvername: "resolver2", type: "ldap", data: { resolver: "resolver2", type: "ldap" } }
      });

      await Promise.resolve(); // Wait for the microtask queue to flush
      TestBed.flushEffects(); // Ensure computed properties are updated

      // Trigger the resource reload
      service.machineresolverResource.reload();
      service.machineresolverResource.value();
      const req = httpMock.expectOne(`${service.machineresolverBaseUrl}`);
      expect(req.request.method).toBe("GET");
      expect(req.request.headers.get("Authorization")).toBe("test-token");
      req.flush(mockResponse);
      await Promise.resolve(); // Wait for the microtask queue to flush
      TestBed.flushEffects(); // Ensure computed properties are updated
      const result = service.machineresolverResource.value();
      expect(result).toEqual(mockResponse);
    });
    it("should handle HTTP errors and notify", async () => {
      authServiceMock.actionAllowed.mockReturnValue(true);
      // Trigger the resource reload
      service.machineresolverResource.reload();
      const req = httpMock.expectOne(`${service.machineresolverBaseUrl}`);
      expect(req.request.method).toBe("GET");
      req.flush({}, { status: 500, statusText: "Internal Server Error" });
      // Wait for the notification to be called
      await new Promise((resolve) => setTimeout(resolve, 0)); // Allow microtasks to complete
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Failed to load machineresolvers.");
      expect(service.machineresolvers()).toEqual([]);
    });
  });
  describe("postTestMachineresolver", () => {
    it("should return null on success", async () => {
      authServiceMock.actionAllowed.mockImplementation((arg) => (arg === "mresolverwrite" ? true : false));
      const promise = service.postTestMachineresolver(testMachineresolver);
      const url = `${service.machineresolverBaseUrl}test`;
      const req = httpMock.expectOne(url);
      expect(req.request.method).toBe("POST");
      req.flush({ result: { value: {} } });
      const res = await promise;
      expect(res).toBeNull();
    });
    it("should return 'post-failed' on error", async () => {
      authServiceMock.actionAllowed.mockImplementation((arg) => (arg === "mresolverwrite" ? true : false));
      const promise = service.postTestMachineresolver(testMachineresolver);
      const url = `${service.machineresolverBaseUrl}test`;
      const req = httpMock.expectOne(url);
      req.flush({ result: { error: { message: "error" } } }, { status: 500, statusText: "error" });
      const res = await promise;
      expect(res).toBe("post-failed");
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Failed to update machineresolver. error");
    });
    it("should return 'not-allowed' if action is not allowed", async () => {
      authServiceMock.actionAllowed.mockImplementation((arg) => (arg === "mresolverwrite" ? false : true));
      const result = await service.postTestMachineresolver(testMachineresolver);
      expect(result).toBe("not-allowed");
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        "You are not allowed to update machineresolvers."
      );
    });
  });
  describe("postMachineresolver", () => {
    it("should return null on success", async () => {
      authServiceMock.actionAllowed.mockImplementation((arg) => (arg === "mresolverwrite" ? true : false));
      const promise = service.postMachineresolver(testMachineresolver);
      const url = `${service.machineresolverBaseUrl}${testMachineresolver.resolvername}`;
      const req = httpMock.expectOne(url);
      expect(req.request.method).toBe("POST");
      req.flush({ result: { value: {} } });
      await promise.then((res) => {
        expect(res).toBeNull();
      });
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Successfully updated machineresolver.");
    });
    it("should return 'post-failed' on error", async () => {
      authServiceMock.actionAllowed.mockImplementation((arg) => (arg === "mresolverwrite" ? true : false));
      const promise = service.postMachineresolver(testMachineresolver);
      const url = `${service.machineresolverBaseUrl}${testMachineresolver.resolvername}`;
      const req = httpMock.expectOne(url);
      req.flush({ result: { error: { message: "error" } } }, { status: 500, statusText: "error" });
      const result = await promise;
      expect(result).toBe("post-failed");
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Failed to update machineresolver. error");
    });
    it("should return 'not-allowed' if action is not allowed", async () => {
      authServiceMock.actionAllowed.mockImplementation((arg) => (arg === "mresolverwrite" ? false : true));
      const result = await service.postMachineresolver(testMachineresolver);
      expect(result).toBe("not-allowed");
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        "You are not allowed to update machineresolvers."
      );
    });
  });
  describe("deleteMachineresolver", () => {
    it("should return null on success", async () => {
      authServiceMock.actionAllowed.mockImplementation((arg) => (arg === "mresolverdelete" ? true : false));
      const promise = service.deleteMachineresolver("test-resolver");
      const url = `${service.machineresolverBaseUrl}test-resolver`;
      const req = httpMock.expectOne(url);
      expect(req.request.method).toBe("DELETE");
      req.flush({ result: { value: {} } });
      const result = await promise;
      expect(result).toBeNull();
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        "Successfully deleted machineresolver: test-resolver."
      );
    });
    it("should return 'post-failed' on error", async () => {
      authServiceMock.actionAllowed.mockImplementation((arg) => (arg === "mresolverdelete" ? true : false));
      const promise = service.deleteMachineresolver("test-resolver");
      const url = `${service.machineresolverBaseUrl}test-resolver`;
      const req = httpMock.expectOne(url);
      req.flush({ result: { error: { message: "error" } } }, { status: 500, statusText: "error" });
      const result = await promise;
      expect(result).toBe("post-failed");
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Failed to delete machineresolver. error");
    });
    it("should return 'not-allowed' if action is not allowed", async () => {
      authServiceMock.actionAllowed.mockImplementation((arg) => (arg === "mresolverdelete" ? false : true));
      const result = await service.deleteMachineresolver("test-resolver");
      expect(result).toBe("not-allowed");
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        "You are not allowed to delete machineresolvers."
      );
    });
  });
});
