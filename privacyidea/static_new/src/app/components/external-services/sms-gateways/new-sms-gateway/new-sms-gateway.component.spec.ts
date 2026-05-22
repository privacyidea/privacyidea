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
import { signal } from "@angular/core";
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { SmsGateway, SmsGatewayService } from "@services/sms-gateway/sms-gateway.service";
import { MockDialogService } from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockSmsGatewayService } from "@testing/mock-services/mock-sms-gateway-service";
import { of } from "rxjs";
import { NewSmsGatewayComponent } from "./new-sms-gateway.component";

describe("NewSmsGatewayComponent", () => {
  let component: NewSmsGatewayComponent;
  let fixture: ComponentFixture<NewSmsGatewayComponent>;
  let smsGatewayServiceMock: any;
  let router: Router;
  let pendingChangesService: MockPendingChangesService;
  let dialogService: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewSmsGatewayComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap({})) }
        },
        { provide: SmsGatewayService, useClass: MockSmsGatewayService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    smsGatewayServiceMock = TestBed.inject(SmsGatewayService);
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);

    (smsGatewayServiceMock.smsProvidersResource as any).value.set({
      result: {
        value: {
          mod1: { parameters: { p1: { description: "desc1" } } }
        }
      }
    });

    fixture = TestBed.createComponent(NewSmsGatewayComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form for create mode", () => {
    expect(component.isEditMode()).toBe(false);
    expect(component.smsModel().name).toBe("");
  });

  it("should update parameters when provider changes", async () => {
    component.smsModel.update(m => ({ ...m, providermodule: "mod1" }));
    fixture.detectChanges();
    await fixture.whenStable();
    expect(component.parametersModel()["p1"]).toBeDefined();
  });

  it("should call save when form is valid", async () => {
    component.smsModel.set({
      name: "test",
      providermodule: "mod1",
      description: ""
    });

    const success = await component.save();

    expect(success).toBe(true);
    expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
  });

  it("Save should handle error", async () => {
    component.smsModel.set({
      name: "test",
      providermodule: "mod1",
      description: ""
    });
    smsGatewayServiceMock.postSmsGateway = jest.fn().mockRejectedValue(new Error("Save failed"));

    const success = await component.save();

    expect(success).toBe(false);
    expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalled();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  describe("onCancel", () => {
    let mockSaveExitDialogRef: any;

    beforeEach(() => {
      mockSaveExitDialogRef = {
        afterClosed: jest.fn()
      };
      dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);
    });

    it("should navigate back directly when there are no changes", () => {
      component.onCancel();

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    });

    it("should open SaveAndExitDialog when there are changes", () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.smsModel.set({
        name: "test",
        providermodule: "mod1",
        description: ""
      });
      // Simulate dirty state by triggering form interaction
      component.smsForm().markAsDirty();

      component.onCancel();

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          component: SaveAndExitDialogComponent,
          data: expect.objectContaining({
            allowSaveExit: true
          })
        })
      );
    });

    it("should navigate back when user selects 'discard' in cancel dialog", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.smsModel.set({
        name: "test",
        providermodule: "mod1",
        description: ""
      });
      component.parametersDirty.set(true);

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    });

    it("should navigate back when user selects 'save-exit' and save succeeds", async () => {
      component.smsModel.set({
        name: "test",
        providermodule: "mod1",
        description: ""
      });
      component.parametersDirty.set(true);
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(true));

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    });

    it("should NOT navigate back when user selects 'save-exit' but save fails", async () => {
      component.smsModel.set({
        name: "test",
        providermodule: "mod1",
        description: ""
      });
      component.parametersDirty.set(true);
      smsGatewayServiceMock.postSmsGateway = jest.fn().mockRejectedValue(new Error("Save failed"));
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(false));

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should do nothing when user selects 'save-exit' but canSave is false", async () => {
      component.smsModel.update(m => ({ ...m, name: "" }));
      component.parametersDirty.set(true);
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(pendingChangesService.save).not.toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should do nothing when user closes dialog without selecting an option", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of(undefined));
      component.smsModel.set({
        name: "test",
        providermodule: "mod1",
        description: ""
      });
      component.parametersDirty.set(true);

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });
  });

  describe("parameters and validation", () => {
    it("parametersValid should be false when a required parameter is missing", () => {
      (smsGatewayServiceMock.smsProvidersResource as any).value.set({
        result: {
          value: {
            mod1: {
              parameters: {
                required_p: { description: "d", required: true },
                optional_p: { description: "d2" }
              }
            }
          }
        }
      });
      component.smsModel.update((m) => ({ ...m, providermodule: "mod1" }));
      component.onProviderChange("mod1");
      expect(component.parametersValid()).toBe(false);
    });

    it("parametersValid should be true when required parameters are filled", () => {
      (smsGatewayServiceMock.smsProvidersResource as any).value.set({
        result: {
          value: {
            mod1: {
              parameters: {
                required_p: { description: "d", required: true }
              }
            }
          }
        }
      });
      component.smsModel.update((m) => ({ ...m, providermodule: "mod1" }));
      component.onProviderChange("mod1");
      component.updateParameter("required_p", "value");
      expect(component.parametersValid()).toBe(true);
      expect(component.parametersDirty()).toBe(true);
    });

    it("updateParameter should update the model and dirty flag", () => {
      component.updateParameter("key1", "value1");
      expect(component.parametersModel()["key1"]).toBe("value1");
      expect(component.parametersDirty()).toBe(true);
    });

    it("clearParameter should reset value and mark dirty", () => {
      component.updateParameter("key1", "value1");
      component.parametersDirty.set(false);
      component.clearParameter("key1");
      expect(component.parametersModel()["key1"]).toBe("");
      expect(component.parametersDirty()).toBe(true);
    });
  });

  describe("custom options and headers", () => {
    it("addOption should add a new option and reset newOptionKey/newOptionValue", () => {
      component.newOptionKey.set("k1");
      component.newOptionValue.set("v1");
      component.addOption();
      expect(component.customOptions).toEqual({ k1: "v1" });
      expect(component.newOptionKey()).toBe("");
      expect(component.newOptionValue()).toBe("");
    });

    it("addOption should not add when key is empty", () => {
      component.addOption();
      expect(component.customOptions).toEqual({});
    });

    it("deleteOption should remove the option", () => {
      component.customOptions = { k1: "v1", k2: "v2" };
      component.deleteOption("k1");
      expect(component.customOptions).toEqual({ k2: "v2" });
    });

    it("addHeader should add a new header", () => {
      component.newHeaderKey.set("h1");
      component.newHeaderValue.set("hv1");
      component.addHeader();
      expect(component.customHeaders).toEqual({ h1: "hv1" });
      expect(component.newHeaderKey()).toBe("");
      expect(component.newHeaderValue()).toBe("");
    });

    it("addHeader should not add when key is empty", () => {
      component.addHeader();
      expect(component.customHeaders).toEqual({});
    });

    it("deleteHeader should remove the header", () => {
      component.customHeaders = { h1: "hv1", h2: "hv2" };
      component.deleteHeader("h2");
      expect(component.customHeaders).toEqual({ h1: "hv1" });
    });

    it("optionRows should return sorted entries", () => {
      component.customOptions = { z: "1", a: "2" };
      expect(component.optionRows).toEqual([
        { key: "a", value: "2" },
        { key: "z", value: "1" }
      ]);
    });

    it("headerRows should return sorted entries", () => {
      component.customHeaders = { b: "1", a: "2" };
      expect(component.headerRows).toEqual([
        { key: "a", value: "2" },
        { key: "b", value: "1" }
      ]);
    });

    it("hasChanges should be true when customOptions are set", () => {
      component.customOptions = { x: "y" };
      expect(component.hasChanges).toBe(true);
    });

    it("hasChanges should be true when customHeaders are set", () => {
      component.customHeaders = { x: "y" };
      expect(component.hasChanges).toBe(true);
    });
  });

  describe("save with custom options/headers and edit mode", () => {
    it("should include option.* and header.* entries in the payload", async () => {
      component.smsModel.set({ name: "gw", providermodule: "mod1", description: "d" });
      component.updateParameter("p1", "v1");
      component.customOptions = { extra: "ext-val" };
      component.customHeaders = { "X-Test": "header-val" };

      await component.save();

      expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "gw",
          module: "mod1",
          description: "d",
          "option.p1": "v1",
          "option.extra": "ext-val",
          "header.X-Test": "header-val"
        })
      );
    });

    it("save should return false when form is invalid", async () => {
      component.smsModel.set({ name: "", providermodule: "", description: "" });
      const result = await component.save();
      expect(result).toBe(false);
      expect(smsGatewayServiceMock.postSmsGateway).not.toHaveBeenCalled();
    });
  });

  describe("edit mode", () => {
    it("onProviderChange in edit mode should fill custom options from data not matching provider parameters", () => {
      (smsGatewayServiceMock.smsProvidersResource as any).value.set({
        result: {
          value: {
            mod1: {
              parameters: { p1: { description: "d", required: true } }
            }
          }
        }
      });
      (component as any).isEditMode.set(true);
      (component as any).data = {
        id: 42,
        name: "edit-gw",
        providermodule: "mod1",
        options: { p1: "fromData", extra: "custom-val" },
        headers: { "X-Auth": "secret" }
      } as SmsGateway;
      component.smsModel.update((m) => ({ ...m, providermodule: "mod1" }));

      component.onProviderChange("mod1");

      expect(component.parametersModel()["p1"]).toBe("fromData");
      expect(component.customOptions).toEqual({ extra: "custom-val" });
      expect(component.customHeaders).toEqual({ "X-Auth": "secret" });
    });

    it("save in edit mode should include the gateway id in the payload", async () => {
      (component as any).isEditMode.set(true);
      (component as any).data = {
        id: 99,
        name: "edit-gw",
        providermodule: "mod1",
        options: {},
        headers: {}
      } as SmsGateway;
      component.smsModel.set({ name: "edit-gw", providermodule: "mod1", description: "x" });

      await component.save();

      expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalledWith(
        expect.objectContaining({ id: 99 })
      );
    });
  });

  describe("providerEntries / parameterEntries", () => {
    it("providerEntries should map current providers to entries", () => {
      (smsGatewayServiceMock.smsProvidersResource as any).value.set({
        result: {
          value: {
            modA: { parameters: {} },
            modB: { parameters: {} }
          }
        }
      });
      const entries = component.providerEntries();
      expect(entries.map((e) => e.key).sort()).toEqual(["modA", "modB"]);
    });

    it("parameterEntries should return entries for currently selected provider", () => {
      component.selectedProvider.set({ parameters: { p1: { description: "d" } as any } });
      const entries = component.parameterEntries();
      expect(entries).toEqual([{ key: "p1", value: { description: "d" } }]);
    });

    it("parameterEntries should return empty array when no provider selected", () => {
      component.selectedProvider.set(undefined);
      expect(component.parameterEntries()).toEqual([]);
    });
  });
});
