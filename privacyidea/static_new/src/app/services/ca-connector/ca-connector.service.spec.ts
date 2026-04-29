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
import { CaConnectorService } from "./ca-connector.service";
import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { environment } from "../../../environments/environment";
import { MockContentService, MockPiResponse } from "../../../testing/mock-services";
import { ContentService } from "../content/content.service";
import { signal } from "@angular/core";

describe("CaConnectorService", () => {
  let service: CaConnectorService;
  let httpMock: HttpTestingController;
  let notificationService: NotificationService;
  let contentService: MockContentService;

  beforeEach(() => {
    const authServiceMock = {
      getHeaders: jest.fn().mockReturnValue({}),
    };
    const notificationServiceMock = {
      openSnackBar: jest.fn(),
      handleResourceError: jest.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authServiceMock },
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: ContentService, useClass: MockContentService}
      ]
    });
    service = TestBed.inject(CaConnectorService);
    httpMock = TestBed.inject(HttpTestingController);
    notificationService = TestBed.inject(NotificationService);
    contentService = TestBed.inject(ContentService) as any as MockContentService;
    contentService.onExternalCaConnectors = signal(true);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should post CA connector", async () => {
    const connector = { connectorname: "test", type: "local", data: {} } as any;
    const promise = service.postCaConnector(connector);

    const req = httpMock.expectOne(`${environment.proxyUrl}/caconnector/test`);
    expect(req.request.method).toBe("POST");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully saved CA connector.");
  });

  it("should delete CA connector", async () => {
    const promise = service.deleteCaConnector("test");

    const req = httpMock.expectOne(`${environment.proxyUrl}/caconnector/test`);
    expect(req.request.method).toBe("DELETE");
    req.flush({ result: { status: true } });

    await promise;
    expect(notificationService.openSnackBar).toHaveBeenCalledWith("Successfully deleted CA connector: test.");
  });

  it("should get CA specific options", async () => {
    const promise = service.getCaSpecificOptions("microsoft", { hostname: "test" });

    const req = httpMock.expectOne(`${environment.proxyUrl}/caconnector/specific/microsoft?hostname=test`);
    expect(req.request.method).toBe("GET");
    req.flush({ result: { value: { available_cas: ["CA1"] } } });

    const result = await promise;
    expect(result).toEqual({ available_cas: ["CA1"] });
  });

  it("should get caConnectors", async () => {
    TestBed.tick();
    let req = httpMock.expectOne((req) => req.url.includes(service.caConnectorBaseUrl));
    let caConnectors = [{connectorname: "test", type: "local", data: {}}];
    req.flush(MockPiResponse.fromValue(caConnectors));
    await Promise.resolve();
    expect(service.caConnectors()).toEqual(caConnectors);

    // Update response
    service.caConnectorResource.reload();
    TestBed.tick();
    req = httpMock.expectOne((req) => req.url.includes(service.caConnectorBaseUrl));
    caConnectors = [{connectorname: "test", type: "local", data: {}}, {connectorname: "test2", type: "local", data: {}}];
    req.flush(MockPiResponse.fromValue(caConnectors));
    await Promise.resolve();
    expect(service.caConnectors()).toEqual(caConnectors);

    // Return previous value for failed response
    service.caConnectorResource.reload();
    TestBed.tick();
    req = httpMock.expectOne((req) => req.url.includes(service.caConnectorBaseUrl));
    req.flush("Error", { status: 500, statusText: "Unexpected error occurred"});
    await Promise.resolve();
    expect(service.caConnectors()).toEqual(caConnectors);
  });

  it("should handle error for caConnectorResource", async () => {
    TestBed.tick();
    const req = httpMock.expectOne((req) => req.url.includes(service.caConnectorBaseUrl));
    req.flush("Error", { status: 403, statusText: "Permission denied"});
    await Promise.resolve();
    expect(service.caConnectors()).toEqual([]);
  });
});
