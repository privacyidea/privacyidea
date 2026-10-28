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
import { By } from "@angular/platform-browser";
import { MatSelect } from "@angular/material/select";
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { CaConnector, CaConnectorService } from "@services/ca-connector/ca-connector.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { MockCaConnectorService, MockDialogService, MockPendingChangesService } from "@testing/mock-services";
import { of } from "rxjs";
import { NewCaConnectorComponent } from "./new-ca-connector.component";

const flush = async (fixture: ComponentFixture<unknown>) => {
  fixture.detectChanges();
  await fixture.whenStable();
  fixture.detectChanges();
};

const checkboxInput = (fixture: ComponentFixture<unknown>, label: string): HTMLInputElement => {
  const checkbox = Array.from(fixture.nativeElement.querySelectorAll("mat-checkbox") as NodeListOf<HTMLElement>).find(
    (el) => el.textContent?.includes(label)
  );
  return checkbox!.querySelector("input") as HTMLInputElement;
};

const clickCheckbox = async (fixture: ComponentFixture<unknown>, label: string) => {
  checkboxInput(fixture, label).click();
  await flush(fixture);
};

const matSelect = (fixture: ComponentFixture<unknown>, index: number): MatSelect =>
  fixture.debugElement.queryAll(By.directive(MatSelect))[index].componentInstance;

const pickOption = async (fixture: ComponentFixture<unknown>, index: number, optionText: string) => {
  matSelect(fixture, index).open();
  await flush(fixture);
  const option = Array.from(document.querySelectorAll("mat-option")).find((o) => o.textContent?.trim() === optionText);
  (option as HTMLElement).click();
  await flush(fixture);
};

const inputOf = (fixture: ComponentFixture<unknown>, placeholder: string): HTMLInputElement =>
  fixture.nativeElement.querySelector(`input[placeholder="${placeholder}"]`) as HTMLInputElement;

const typeInto = async (fixture: ComponentFixture<unknown>, input: HTMLInputElement, value: string) => {
  input.value = value;
  input.dispatchEvent(new Event("input"));
  await flush(fixture);
};

const loadCasButton = (fixture: ComponentFixture<unknown>): HTMLButtonElement =>
  Array.from(fixture.nativeElement.querySelectorAll("button") as NodeListOf<HTMLButtonElement>).find((b) =>
    b.textContent?.includes("Get Available CAs")
  )!;

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
    expect(caConnectorServiceMock.postCaConnector.mock.calls[0][0]?.data["cacert"]).toBeUndefined();
  });

  it("hasChanges should reflect form dirty state", async () => {
    expect(component.hasChanges).toBe(false);
    await pickOption(fixture, 0, "Microsoft");
    expect(component.hasChanges).toBe(true);
  });

  describe("bound controls", () => {
    afterEach(() => {
      document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
    });

    it("writes the type select to the model and marks the form dirty", async () => {
      await pickOption(fixture, 0, "Microsoft");
      expect(component.caConnectorModel().type).toBe("microsoft");
      expect(component.caConnectorForm.type().dirty()).toBe(true);
      expect(component.hasChanges).toBe(true);
    });

    it("shows the model type in the select", async () => {
      component.caConnectorModel.update((m) => ({ ...m, type: "microsoft" }));
      await flush(fixture);
      expect(matSelect(fixture, 0).value).toBe("microsoft");
    });

    it.each([
      ["Use HTTP proxy", "http_proxy"],
      ["Use SSL", "use_ssl"]
    ] as const)("%s writes %s to the model and marks the form dirty", async (label, field) => {
      component.caConnectorModel.update((m) => ({ ...m, type: "microsoft" }));
      await flush(fixture);
      expect(component.hasChanges).toBe(false);
      await clickCheckbox(fixture, label);
      expect(component.caConnectorModel()[field]).toBe(true);
      expect(component.caConnectorForm[field]().dirty()).toBe(true);
      expect(component.hasChanges).toBe(true);
    });

    it("shows the SSL fields once Use SSL is checked", async () => {
      component.caConnectorModel.update((m) => ({ ...m, type: "microsoft" }));
      await flush(fixture);
      expect(inputOf(fixture, "/etc/privacyidea/ca/ca.crt")).toBeNull();
      await clickCheckbox(fixture, "Use SSL");
      expect(inputOf(fixture, "/etc/privacyidea/ca/ca.crt")).not.toBeNull();
    });

    it("writes the Domain CA select to the model and marks it dirty", async () => {
      component.caConnectorModel.update((m) => ({ ...m, type: "microsoft", hostname: "h", port: "1" }));
      component.availableCas.set(["CA1", "CA2"]);
      await flush(fixture);
      expect(
        component.caConnectorForm
          .ca()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["required"]);
      await pickOption(fixture, 1, "CA2");
      expect(component.caConnectorModel().ca).toBe("CA2");
      expect(component.caConnectorForm.ca().dirty()).toBe(true);
      expect(component.caConnectorForm.ca().errors()).toEqual([]);
    });

    it("marks the form dirty when a clear button empties a field", async () => {
      component.caConnectorModel.update((m) => ({ ...m, cacert: "/etc/cacert.pem" }));
      await flush(fixture);
      expect(component.hasChanges).toBe(false);
      const clear = inputOf(fixture, "/etc/cacert.pem").closest("app-clearable-input")!.querySelector("button");
      (clear as HTMLButtonElement).click();
      await flush(fixture);
      expect(component.caConnectorModel().cacert).toBe("");
      expect(component.hasChanges).toBe(true);
    });

    it("clears the 'openssl.cnf' field through its clear button", async () => {
      component.caConnectorModel.update((m) => ({ ...m, "openssl.cnf": "/etc/openssl.cnf" }));
      await flush(fixture);
      const clear = inputOf(fixture, "/etc/openssl.cnf").closest("app-clearable-input")!.querySelector("button");
      (clear as HTMLButtonElement).click();
      await flush(fixture);
      expect(component.caConnectorModel()["openssl.cnf"]).toBe("");
      expect(component.caConnectorForm["openssl.cnf"]().dirty()).toBe(true);
    });

    it("rejects a connector name with invalid characters", async () => {
      await typeInto(fixture, inputOf(fixture, "MyConnector1"), "bad name");
      expect(
        component.caConnectorForm
          .connectorname()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["pattern"]);
    });

    it.each([
      ["30", "CRL_Validity_Period"],
      ["10", "CRL_Overlap_Period"]
    ] as const)("renders the parse message of the %s field once it is touched", async (placeholder, field) => {
      const input = inputOf(fixture, placeholder);
      jest.spyOn(input, "validity", "get").mockReturnValue({ badInput: true } as ValidityState);
      await typeInto(fixture, input, "");
      expect(
        component.caConnectorForm[field]()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["parse"]);
      input.dispatchEvent(new Event("blur"));
      await flush(fixture);
      expect(fixture.nativeElement.textContent).toContain("Enter a valid number");
    });

    describe("Get Available CAs button", () => {
      beforeEach(async () => {
        component.caConnectorModel.update((m) => ({ ...m, type: "microsoft" }));
        await flush(fixture);
      });

      it("is disabled until hostname and port are valid", async () => {
        expect(loadCasButton(fixture).disabled).toBe(true);
        await typeInto(fixture, inputOf(fixture, "example.net"), "ms.example");
        expect(loadCasButton(fixture).disabled).toBe(true);
        await typeInto(fixture, inputOf(fixture, "1234"), "443");
        expect(component.canLoadAvailableCas()).toBe(true);
        expect(loadCasButton(fixture).disabled).toBe(false);
      });

      it("requests the CAs when clicked", async () => {
        await typeInto(fixture, inputOf(fixture, "example.net"), "ms.example");
        await typeInto(fixture, inputOf(fixture, "1234"), "443");
        loadCasButton(fixture).click();
        await flush(fixture);
        expect(caConnectorServiceMock.getCaSpecificOptions).toHaveBeenCalledWith(
          "microsoft",
          expect.objectContaining({ hostname: "ms.example", port: "443" })
        );
        expect(component.availableCas()).toEqual(["CA1", "CA2"]);
      });

      it("stays disabled while the port holds text the browser cannot parse", async () => {
        await typeInto(fixture, inputOf(fixture, "example.net"), "ms.example");
        await typeInto(fixture, inputOf(fixture, "1234"), "443");
        const port = inputOf(fixture, "1234");
        jest.spyOn(port, "validity", "get").mockReturnValue({ badInput: true } as ValidityState);
        await typeInto(fixture, port, "");
        expect(component.canLoadAvailableCas()).toBe(false);
        expect(loadCasButton(fixture).disabled).toBe(true);
      });

      it("does not request the CAs for an invalid form", () => {
        caConnectorServiceMock.getCaSpecificOptions.mockClear();
        component.loadAvailableCas();
        expect(caConnectorServiceMock.getCaSpecificOptions).not.toHaveBeenCalled();
      });
    });
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

  it("disables the type select in edit mode", () => {
    expect(matSelect(fixture, 0).disabled).toBe(true);
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

    it("should open the SaveAndExit dialog when there are changes", async () => {
      mockDialogRef.afterClosed.mockReturnValue(of(undefined));
      await typeInto(fixture, inputOf(fixture, "/etc/cacert.pem"), "/etc/other.pem");
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

  describe("deleteConnector", () => {
    let dialog: MockDialogService;
    let pending: MockPendingChangesService;
    let service: MockCaConnectorService;
    let navigateSpy: jest.SpyInstance;

    beforeEach(() => {
      dialog = TestBed.inject(DialogService) as unknown as MockDialogService;
      pending = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
      service = TestBed.inject(CaConnectorService) as unknown as MockCaConnectorService;
      navigateSpy = jest.spyOn(TestBed.inject(Router), "navigateByUrl").mockResolvedValue(true);
    });

    it("does nothing without an identifier", async () => {
      component["editConnectorName"] = null;
      await component.deleteConnector();
      expect(dialog.confirmDelete).not.toHaveBeenCalled();
      expect(service.deleteCaConnector).not.toHaveBeenCalled();
    });

    it("does not delete when the confirmation is cancelled", async () => {
      dialog.confirmDelete.mockResolvedValue(false);
      await component.deleteConnector();
      expect(service.deleteCaConnector).not.toHaveBeenCalled();
      expect(navigateSpy).not.toHaveBeenCalled();
    });

    it("deletes after confirmation and navigates back to the list", async () => {
      await component.deleteConnector();
      expect(dialog.confirmDelete).toHaveBeenCalledWith(expect.objectContaining({ items: ["edit-me"] }));
      expect(service.deleteCaConnector).toHaveBeenCalledWith("edit-me");
      expect(pending.clearAllRegistrations).toHaveBeenCalled();
      expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS);
    });

    it("stays on the page when the deletion fails", async () => {
      service.deleteCaConnector.mockRejectedValue(new Error("delete failed"));
      await component.deleteConnector();
      expect(pending.clearAllRegistrations).not.toHaveBeenCalled();
      expect(navigateSpy).not.toHaveBeenCalled();
    });
  });
});

describe("NewCaConnectorComponent edit mode of a Microsoft connector", () => {
  let component: NewCaConnectorComponent;
  let fixture: ComponentFixture<NewCaConnectorComponent>;
  let caConnectorServiceMock: MockCaConnectorService;

  const msConnector: CaConnector = {
    connectorname: "ms-1",
    type: "microsoft",
    data: { hostname: "ms.example", port: "443", use_ssl: false, http_proxy: false }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewCaConnectorComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ name: "ms-1" })) } },
        { provide: CaConnectorService, useClass: MockCaConnectorService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();
    caConnectorServiceMock = TestBed.inject(CaConnectorService) as unknown as MockCaConnectorService;
    caConnectorServiceMock.getCaSpecificOptions.mockResolvedValue({ available_cas: ["CA1"] });
    caConnectorServiceMock.caConnectors.set([msConnector]);
    fixture = TestBed.createComponent(NewCaConnectorComponent);
    component = fixture.componentInstance;
    await flush(fixture);
  });

  it("loads the available CAs of the stored connector", () => {
    expect(caConnectorServiceMock.getCaSpecificOptions).toHaveBeenCalledWith(
      "microsoft",
      expect.objectContaining({ hostname: "ms.example", port: "443" })
    );
  });

  it("keeps a checkbox edit when the connector list is reloaded", async () => {
    await clickCheckbox(fixture, "Use HTTP proxy");
    expect(component.caConnectorModel().http_proxy).toBe(true);

    caConnectorServiceMock.caConnectors.set([{ ...msConnector, data: { ...msConnector.data, hostname: "other" } }]);
    await flush(fixture);

    expect(component.caConnectorModel().http_proxy).toBe(true);
    expect(component.caConnectorModel().hostname).toBe("ms.example");
  });

  it("re-initializes from a reloaded list while the form is pristine", async () => {
    caConnectorServiceMock.caConnectors.set([{ ...msConnector, data: { ...msConnector.data, hostname: "other" } }]);
    await flush(fixture);
    expect(component.caConnectorModel().hostname).toBe("other");
    expect(component.hasChanges).toBe(false);
  });
});
