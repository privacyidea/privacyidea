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
import { NewCaConnectorComponent } from "./new-ca-connector.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { CaConnectorService } from "../../../../services/ca-connector/ca-connector.service";
import { MockCaConnectorService } from "../../../../../testing/mock-services/mock-ca-connector-service";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "../../../../route_paths";
import { MockPendingChangesService } from "../../../../../testing/mock-services";

describe("NewCaConnectorComponent", () => {
  let component: NewCaConnectorComponent;
  let fixture: ComponentFixture<NewCaConnectorComponent>;
  let caConnectorServiceMock: any;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewCaConnectorComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: CaConnectorService, useClass: MockCaConnectorService },
        { provide: PendingChangesService, useClass: MockPendingChangesService }
      ]
    }).compileComponents();

    caConnectorServiceMock = TestBed.inject(CaConnectorService);
    caConnectorServiceMock.getCaSpecificOptions.mockResolvedValue({ available_cas: ["CA1", "CA2"] });
    router = TestBed.inject(Router);

    fixture = TestBed.createComponent(NewCaConnectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form with local type by default", () => {
    expect(component.caConnectorForm.get("type")?.value).toBe("local");
    expect(component.caConnectorForm.get("cacert")?.validator).toBeDefined();
  });

  it("should update validators when type changes", () => {
    component.caConnectorForm.get("type")?.setValue("microsoft");
    expect(component.caConnectorForm.get("cacert")?.validator).toBeNull();
    expect(component.caConnectorForm.get("hostname")?.validator).toBeDefined();
  });

  it("should load available CAs for microsoft type", async () => {
    component.caConnectorForm.get("type")?.setValue("microsoft");
    component.caConnectorForm.patchValue({ hostname: "test", port: "123" });

    component.loadAvailableCas();
    await caConnectorServiceMock.getCaSpecificOptions.mock.results[0].value;

    expect(caConnectorServiceMock.getCaSpecificOptions).toHaveBeenCalledWith(
      "microsoft",
      expect.objectContaining({ hostname: "test", port: "123" })
    );
    expect(component.availableCas()).toEqual(["CA1", "CA2"]);
  });

  it("should call save when form is valid", async () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.caConnectorForm.patchValue({
      connectorname: "test",
      type: "local",
      cacert: "cert",
      cakey: "key",
      "openssl.cnf": "cnf"
    });

    const success = await component.save();

    expect(success).toBe(true);
    expect(caConnectorServiceMock.postCaConnector).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
  });

  it("save should return false on error", async () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.caConnectorForm.patchValue({
      connectorname: "test",
      type: "local",
      cacert: "cert",
      cakey: "key",
      "openssl.cnf": "cnf"
    });
    caConnectorServiceMock.postCaConnector = jest.fn().mockRejectedValue(new Error("Save failed"));

    const success = await component.save();

    expect(success).toBe(false);
    expect(caConnectorServiceMock.postCaConnector).toHaveBeenCalled();
    expect(navigateSpy).not.toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
  });
});
