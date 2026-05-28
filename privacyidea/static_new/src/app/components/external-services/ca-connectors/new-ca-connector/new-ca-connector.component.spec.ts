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
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { CaConnector, CaConnectorService } from "@services/ca-connector/ca-connector.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { MockCaConnectorService, MockDialogService, MockPendingChangesService } from "@testing/mock-services";
import { of } from "rxjs";
import { NewCaConnectorComponent } from "./new-ca-connector.component";

describe("NewCaConnectorComponent", () => {
  let component: NewCaConnectorComponent;
  let fixture: ComponentFixture<NewCaConnectorComponent>;
  let caConnectorServiceMock: MockCaConnectorService;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewCaConnectorComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: CaConnectorService, useClass: MockCaConnectorService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService }
      ]
    }).compileComponents();

    caConnectorServiceMock = TestBed.inject(CaConnectorService) as unknown as MockCaConnectorService;
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
    expect(component.caConnectorModel().type).toBe("local");
    // cacert is required when type is local
    expect(
      component.caConnectorForm
        .cacert()
        .errors()
        .some((e) => e.kind === "required")
    ).toBe(true);
  });

  it("should update validators when type changes", () => {
    component.caConnectorModel.update((m) => ({ ...m, type: "microsoft" }));
    // cacert should no longer be required for microsoft type
    expect(
      component.caConnectorForm
        .cacert()
        .errors()
        .some((e) => e.kind === "required")
    ).toBe(false);
    // hostname should be required for microsoft type
    expect(
      component.caConnectorForm
        .hostname()
        .errors()
        .some((e) => e.kind === "required")
    ).toBe(true);
  });

  it("should load available CAs for microsoft type", async () => {
    component.caConnectorModel.update((m) => ({ ...m, type: "microsoft", hostname: "test", port: "123" }));

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
    component.caConnectorModel.update((m) => ({
      ...m,
      connectorname: "test",
      type: "local",
      cacert: "cert",
      cakey: "key",
      "openssl.cnf": "cnf"
    }));

    const success = await component.save();

    expect(success).toBe(true);
    expect(caConnectorServiceMock.postCaConnector).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
  });

  it("save should return false on error", async () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.caConnectorModel.update((m) => ({
      ...m,
      connectorname: "test",
      type: "local",
      cacert: "cert",
      cakey: "key",
      "openssl.cnf": "cnf"
    }));
    caConnectorServiceMock.postCaConnector = jest.fn().mockRejectedValue(new Error("Save failed"));

    const success = await component.save();

    expect(success).toBe(false);
    expect(caConnectorServiceMock.postCaConnector).toHaveBeenCalled();
    expect(navigateSpy).not.toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
  });

  it("save should return false when form is invalid", async () => {
    component.caConnectorModel.update((m) => ({ ...m, connectorname: "" }));
    const result = await component.save();
    expect(result).toBe(false);
    expect(caConnectorServiceMock.postCaConnector).not.toHaveBeenCalled();
  });

  it("save with microsoft type should serialize microsoft fields", async () => {
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.caConnectorModel.set({
      connectorname: "ms-1",
      type: "microsoft",
      cacert: "",
      cakey: "",
      "openssl.cnf": "",
      templates: "",
      WorkingDir: "",
      CSRDir: "",
      CertificateDir: "",
      CRL: "",
      CRL_Validity_Period: "",
      CRL_Overlap_Period: "",
      hostname: "ms.example",
      port: "443",
      http_proxy: true,
      use_ssl: true,
      ssl_ca_cert: "/path/to/ca",
      ssl_client_cert: "",
      ssl_client_key: "",
      ssl_client_key_password: "",
      ca: ""
    });

    const result = await component.save();
    expect(result).toBe(true);
    expect(caConnectorServiceMock.postCaConnector).toHaveBeenCalledWith(
      expect.objectContaining({
        connectorname: "ms-1",
        type: "microsoft",
        data: expect.objectContaining({
          hostname: "ms.example",
          port: "443",
          http_proxy: true,
          use_ssl: true,
          ssl_ca_cert: "/path/to/ca"
        })
      })
    );
    expect(caConnectorServiceMock.postCaConnector.mock.calls[0][0]?.data.cacert).toBeUndefined();
  });

  it("hasChanges should reflect form dirty state", () => {
    expect(component.hasChanges).toBe(false);
    component.caConnectorForm().markAsDirty();
    expect(component.hasChanges).toBe(true);
  });

  it("canSave should reflect form validity", () => {
    expect(component.canSave).toBe(false);
    component.caConnectorModel.update((m) => ({
      ...m,
      connectorname: "x",
      type: "local",
      cacert: "c",
      cakey: "k",
      "openssl.cnf": "o"
    }));
    expect(component.canSave).toBe(true);
  });
});

describe("NewCaConnectorComponent edit mode", () => {
  let component: NewCaConnectorComponent;
  let fixture: ComponentFixture<NewCaConnectorComponent>;
  let caConnectorServiceMock: MockCaConnectorService;
  let dialogService: MockDialogService;
  let pendingChangesService: MockPendingChangesService;
  let router: Router;

  const existingConnector: CaConnector = {
    connectorname: "edit-me",
    type: "local",
    data: {
      cacert: "c",
      cakey: "k",
      "openssl.cnf": "o",
      WorkingDir: "/tmp"
    }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewCaConnectorComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap({ name: "edit-me" })) }
        },
        { provide: CaConnectorService, useClass: MockCaConnectorService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    caConnectorServiceMock = TestBed.inject(CaConnectorService) as unknown as MockCaConnectorService;
    caConnectorServiceMock.caConnectors.set([existingConnector]);
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);

    fixture = TestBed.createComponent(NewCaConnectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should populate the model from the existing connector and lock identity fields", () => {
    expect(component.isEditMode()).toBe(true);
    expect(component.caConnectorModel().connectorname).toBe("edit-me");
    expect(component.caConnectorModel().cacert).toBe("c");
    expect(component.caConnectorModel().WorkingDir).toBe("/tmp");
    expect(component.caConnectorForm.connectorname().disabled()).toBe(true);
    expect(component.caConnectorForm.type().disabled()).toBe(true);
  });

  it("loadAvailableCas should populate availableCas on success and clear loading on failure", async () => {
    component.caConnectorModel.update((m) => ({
      ...m,
      type: "microsoft",
      hostname: "host",
      port: "443"
    }));
    caConnectorServiceMock.getCaSpecificOptions.mockResolvedValueOnce({ available_cas: ["CA-x"] });
    component.loadAvailableCas();
    await caConnectorServiceMock.getCaSpecificOptions.mock.results[0].value;
    expect(component.availableCas()).toEqual(["CA-x"]);
    expect(component.isLoadingCas()).toBe(false);

    caConnectorServiceMock.getCaSpecificOptions.mockRejectedValueOnce(new Error("fail"));
    component.loadAvailableCas();
    await expect(caConnectorServiceMock.getCaSpecificOptions.mock.results[1].value).rejects.toThrow("fail");
    await new Promise((r) => setTimeout(r, 0));
    expect(component.isLoadingCas()).toBe(false);
  });

  it("loadAvailableCas should not fire request when hostname or port missing", () => {
    component.caConnectorModel.update((m) => ({ ...m, hostname: "", port: "" }));
    caConnectorServiceMock.getCaSpecificOptions.mockClear();
    component.loadAvailableCas();
    expect(caConnectorServiceMock.getCaSpecificOptions).not.toHaveBeenCalled();
  });

  describe("onCancel", () => {
    let mockDialogRef: { afterClosed: jest.Mock };

    beforeEach(() => {
      mockDialogRef = { afterClosed: jest.fn() };
      dialogService.openDialog.mockReturnValue(mockDialogRef);
    });

    it("should navigate immediately when there are no changes", () => {
      component.onCancel();
      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
    });

    it("should open the SaveAndExit dialog when there are changes", () => {
      mockDialogRef.afterClosed.mockReturnValue(of(undefined));
      component.caConnectorForm().markAsDirty();
      component.onCancel();
      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ component: SaveAndExitDialogComponent })
      );
    });

    it("should navigate after user selects 'discard'", async () => {
      mockDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.caConnectorForm().markAsDirty();
      component.onCancel();
      await new Promise((r) => setTimeout(r, 0));
      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
    });

    it("should save and navigate when user selects 'save-exit' and save succeeds", async () => {
      mockDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      component.caConnectorForm().markAsDirty();
      pendingChangesService.save = jest.fn().mockReturnValue(Promise.resolve(true));
      component.onCancel();
      await new Promise((r) => setTimeout(r, 0));
      expect(pendingChangesService.save).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
    });

    it("should NOT navigate when 'save-exit' selected but save fails", async () => {
      mockDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      component.caConnectorForm().markAsDirty();
      pendingChangesService.save = jest.fn().mockReturnValue(Promise.resolve(false));
      component.onCancel();
      await new Promise((r) => setTimeout(r, 0));
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should do nothing when 'save-exit' selected but canSave is false", async () => {
      mockDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      component.caConnectorModel.update((m) => ({ ...m, cacert: "" }));
      component.caConnectorForm().markAsDirty();
      pendingChangesService.save = jest.fn();
      component.onCancel();
      await new Promise((r) => setTimeout(r, 0));
      expect(pendingChangesService.save).not.toHaveBeenCalled();
    });
  });
});
