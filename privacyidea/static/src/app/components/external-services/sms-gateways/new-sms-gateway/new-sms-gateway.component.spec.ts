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
import { WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatDialogRef } from "@angular/material/dialog";
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import {
  SmsGateway,
  SmsGatewayService,
  SmsProviderParameter,
  SmsProviders
} from "@services/sms-gateway/sms-gateway.service";
import { MockDialogService } from "@testing/mock-services";
import { MockPendingChangesService } from "@testing/mock-services/mock-pending-changes-service";
import { MockSmsGatewayService } from "@testing/mock-services/mock-sms-gateway-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { Observable, of } from "rxjs";
import { NewSmsGatewayComponent } from "./new-sms-gateway.component";

type ProvidersValueSignal = WritableSignal<PiResponse<SmsProviders> | undefined>;
const providersValueSignal = (mock: MockSmsGatewayService): ProvidersValueSignal =>
  mock.smsProvidersResource.value as ProvidersValueSignal;

interface ComponentInternals {
  data: SmsGateway | null;
}
const internals = (component: NewSmsGatewayComponent): ComponentInternals => component as unknown as ComponentInternals;

const flush = async (fixture: ComponentFixture<unknown>) => {
  fixture.detectChanges();
  await fixture.whenStable();
  fixture.detectChanges();
};

/** The mat-form-field with the given label. */
const formFieldOf = (fixture: ComponentFixture<unknown>, label: string): HTMLElement => {
  const fields = Array.from(fixture.nativeElement.querySelectorAll("mat-form-field") as NodeListOf<HTMLElement>);
  return fields.find((el) => el.querySelector("mat-label")?.textContent?.trim() === label)!;
};

const controlOf = (fixture: ComponentFixture<unknown>, label: string): HTMLInputElement | HTMLTextAreaElement =>
  formFieldOf(fixture, label).querySelector("input, textarea") as HTMLInputElement | HTMLTextAreaElement;

const typeInto = async (fixture: ComponentFixture<unknown>, label: string, value: string) => {
  const control = controlOf(fixture, label);
  control.value = value;
  control.dispatchEvent(new Event("input"));
  await flush(fixture);
};

const clearButtonOf = (fixture: ComponentFixture<unknown>, label: string): HTMLButtonElement =>
  formFieldOf(fixture, label).querySelector("app-clearable-input button") as HTMLButtonElement;

const pickOption = async (fixture: ComponentFixture<unknown>, label: string, optionText: string) => {
  (formFieldOf(fixture, label).querySelector(".mat-mdc-select-trigger") as HTMLElement).click();
  await flush(fixture);
  const option = Array.from(document.querySelectorAll("mat-option") as NodeListOf<HTMLElement>).find(
    (el) => el.textContent?.trim() === optionText
  )!;
  option.click();
  await flush(fixture);
};

/** The footer row of the options table (index 0) or the headers table (index 1). */
const footerRow = (fixture: ComponentFixture<unknown>, index: number): HTMLElement =>
  fixture.nativeElement.querySelectorAll("tr.add-footer-row")[index] as HTMLElement;

const addButtonOf = (fixture: ComponentFixture<unknown>, index: number): HTMLButtonElement =>
  footerRow(fixture, index).querySelector("button[aria-label='Add']") as HTMLButtonElement;

const saveButton = (fixture: ComponentFixture<unknown>): HTMLButtonElement =>
  fixture.nativeElement.querySelector("button.action-button-primary") as HTMLButtonElement;

const requiredProviders: SmsProviders = {
  mod1: {
    parameters: {
      required_p: { description: "d", required: true },
      optional_p: { description: "d2" }
    },
    options_allowed: true,
    headers_allowed: true
  }
};

const existingGateway: SmsGateway = {
  id: 5,
  name: "edit-gw",
  description: "stored",
  providermodule: "mod1",
  options: { required_p: "stored-required", optional_p: "stored-optional", extra: "custom-val" },
  headers: { "X-Auth": "token" },
  secret_options: ["extra"]
};

describe("NewSmsGatewayComponent", () => {
  let component: NewSmsGatewayComponent;
  let fixture: ComponentFixture<NewSmsGatewayComponent>;
  let smsGatewayServiceMock: MockSmsGatewayService;
  let router: Router;
  let pendingChangesService: MockPendingChangesService;
  let dialogService: MockDialogService;

  const setProviders = (providers: SmsProviders) =>
    providersValueSignal(smsGatewayServiceMock).set(MockPiResponse.fromValue(providers));

  const setup = async (options: { name?: string; gateways?: SmsGateway[]; providers?: SmsProviders } = {}) => {
    await TestBed.configureTestingModule({
      imports: [NewSmsGatewayComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap(options.name ? { name: options.name } : {})) }
        },
        { provide: SmsGatewayService, useClass: MockSmsGatewayService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    smsGatewayServiceMock = TestBed.inject(SmsGatewayService) as unknown as MockSmsGatewayService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);

    setProviders(options.providers ?? { mod1: { parameters: { p1: { description: "desc1" } } } });
    smsGatewayServiceMock.smsGateways.set(options.gateways ?? []);

    fixture = TestBed.createComponent(NewSmsGatewayComponent);
    component = fixture.componentInstance;
    await flush(fixture);
  };

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe("create mode", () => {
    beforeEach(async () => setup());

    it("should create", () => {
      expect(component).toBeTruthy();
    });

    it("should initialize form for create mode", () => {
      expect(component.isEditMode()).toBe(false);
      expect(component.smsModel().name).toBe("");
      expect(component.smsModel().parameters).toEqual({});
    });

    it("should update parameters when provider changes", async () => {
      component.smsModel.update((m) => ({ ...m, providermodule: "mod1" }));
      await flush(fixture);
      expect(component.smsModel().parameters).toEqual({ p1: "" });
      expect(component.selectedProvider()).toBeDefined();
    });

    it("should call save when form is valid", async () => {
      component.smsModel.set({ name: "test", providermodule: "mod1", description: "", parameters: {} });

      const success = await component.save();

      expect(success).toBe(true);
      expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    });

    it("Save should handle error", async () => {
      component.smsModel.set({ name: "test", providermodule: "mod1", description: "", parameters: {} });
      smsGatewayServiceMock.postSmsGateway = jest.fn().mockRejectedValue(new Error("Save failed"));

      const success = await component.save();

      expect(success).toBe(false);
      expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("registers the pending-changes callbacks on the form state", async () => {
      const hasChanges = pendingChangesService.registerHasChanges.mock.calls[0][0] as () => boolean;
      const validChanges = pendingChangesService.registerValidChanges.mock.calls[0][0] as () => boolean;
      expect(hasChanges()).toBe(false);
      expect(validChanges()).toBe(false);
      await typeInto(fixture, "Name", "gw");
      await pickOption(fixture, "Provider Module", "mod1");
      expect(hasChanges()).toBe(true);
      expect(validChanges()).toBe(true);
    });
  });

  describe("name and provider module", () => {
    beforeEach(async () => setup());

    it("shows the required error for the name once touched", async () => {
      const name = controlOf(fixture, "Name");
      name.dispatchEvent(new Event("blur"));
      await flush(fixture);
      expect(
        component.smsForm
          .name()
          .errors()
          .map((e) => e.kind)
      ).toContain("required");
      expect(formFieldOf(fixture, "Name").textContent).toContain("Name is required");
    });

    it("rejects invalid characters in the name", async () => {
      await typeInto(fixture, "Name", "bad name");
      controlOf(fixture, "Name").dispatchEvent(new Event("blur"));
      await flush(fixture);
      expect(
        component.smsForm
          .name()
          .errors()
          .map((e) => e.kind)
      ).toContain("pattern");
      expect(formFieldOf(fixture, "Name").textContent).toContain("invalid characters");
    });

    it("writes a typed name to the model and marks the form dirty", async () => {
      await typeInto(fixture, "Name", "gw");
      expect(component.smsModel().name).toBe("gw");
      expect(component.smsForm.name().dirty()).toBe(true);
      expect(component.hasChanges).toBe(true);
    });

    it("clears the name through the clear button and keeps the form dirty", async () => {
      component.smsModel.update((m) => ({ ...m, name: "gw" }));
      await flush(fixture);
      expect(component.hasChanges).toBe(false);
      clearButtonOf(fixture, "Name").click();
      await flush(fixture);
      expect(component.smsModel().name).toBe("");
      expect(component.hasChanges).toBe(true);
    });

    it("selects the provider module through the select and marks the form dirty", async () => {
      await pickOption(fixture, "Provider Module", "mod1");
      expect(component.smsModel().providermodule).toBe("mod1");
      expect(component.smsForm.providermodule().dirty()).toBe(true);
      expect(component.hasChanges).toBe(true);
    });

    it("shows the required error for the provider module once touched", async () => {
      await component.save();
      await flush(fixture);
      expect(
        component.smsForm
          .providermodule()
          .errors()
          .map((e) => e.kind)
      ).toContain("required");
      expect(formFieldOf(fixture, "Provider Module").textContent).toContain("Provider Module is required");
    });

    it("writes the description through the textarea and clears it with the clear button", async () => {
      await typeInto(fixture, "Description", "some text");
      expect(component.smsModel().description).toBe("some text");
      clearButtonOf(fixture, "Description").click();
      await flush(fixture);
      expect(component.smsModel().description).toBe("");
      expect(component.smsForm.description().dirty()).toBe(true);
    });
  });

  describe("onCancel", () => {
    let mockSaveExitDialogRef: { afterClosed: jest.Mock<Observable<string | undefined>> };

    beforeEach(async () => {
      await setup();
      mockSaveExitDialogRef = {
        afterClosed: jest.fn()
      };
      dialogService.openDialog.mockReturnValue(
        mockSaveExitDialogRef as unknown as MatDialogRef<SaveAndExitDialogComponent>
      );
    });

    it("should navigate back directly when there are no changes", () => {
      component.onCancel();

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    });

    it("should open SaveAndExitDialog when a field was edited", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      await typeInto(fixture, "Name", "test");

      component.onCancel();

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          component: SaveAndExitDialogComponent,
          data: expect.objectContaining({
            allowSaveExit: true,
            saveExitDisabled: true
          })
        })
      );
    });

    it("should navigate back when user selects 'discard' in cancel dialog", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      await typeInto(fixture, "Name", "test");

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    });

    it("should navigate back when user selects 'save-exit' and save succeeds", async () => {
      await typeInto(fixture, "Name", "test");
      await pickOption(fixture, "Provider Module", "mod1");
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(true));

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    });

    it("should NOT navigate back when user selects 'save-exit' but save fails", async () => {
      await typeInto(fixture, "Name", "test");
      await pickOption(fixture, "Provider Module", "mod1");
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(false));

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should do nothing when user selects 'save-exit' but canSave is false", async () => {
      await typeInto(fixture, "Name", "test");
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(pendingChangesService.save).not.toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should do nothing when user closes dialog without selecting an option", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of(undefined));
      await typeInto(fixture, "Name", "test");

      component.onCancel();

      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should warn when only a provider parameter was typed", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of(undefined));
      component.smsModel.update((m) => ({ ...m, providermodule: "mod1" }));
      await flush(fixture);
      expect(component.hasChanges).toBe(false);
      await typeInto(fixture, "p1", "typed");

      component.onCancel();

      expect(dialogService.openDialog).toHaveBeenCalled();
    });
  });

  describe("parameters", () => {
    beforeEach(async () => {
      await setup({ providers: requiredProviders });
      component.smsModel.update((m) => ({ ...m, name: "gw", providermodule: "mod1" }));
      await flush(fixture);
    });

    it("creates one field per provider parameter", () => {
      expect(Object.keys(component.smsModel().parameters)).toEqual(["required_p", "optional_p"]);
      expect(component.parameterField("required_p")).toBeDefined();
      expect(component.parameterField("optional_p")).toBeDefined();
      expect(controlOf(fixture, "required_p")).toBeTruthy();
    });

    it("returns no field for a key the model does not hold", () => {
      expect(component.parameterField("unknown")).toBeUndefined();
    });

    it("blocks saving while a required parameter is empty", async () => {
      expect(
        component.smsForm.parameters["required_p"]()
          .errors()
          .map((e) => e.kind)
      ).toContain("required");
      expect(component.smsForm.parameters["optional_p"]().errors()).toEqual([]);
      expect(component.canSave).toBe(false);
      expect(saveButton(fixture).disabled).toBe(true);

      await component.save();

      expect(smsGatewayServiceMock.postSmsGateway).not.toHaveBeenCalled();
    });

    it("renders the required error of a parameter after a failed save", async () => {
      await component.save();
      await flush(fixture);
      expect(component.smsForm.parameters["required_p"]().touched()).toBe(true);
      expect(formFieldOf(fixture, "required_p").textContent).toContain("required_p is required");
      expect(formFieldOf(fixture, "optional_p").textContent).not.toContain("is required");
    });

    it("enables saving once the required parameter is typed", async () => {
      await typeInto(fixture, "required_p", "value");
      expect(component.smsModel().parameters["required_p"]).toBe("value");
      expect(component.smsForm.parameters["required_p"]().dirty()).toBe(true);
      expect(component.canSave).toBe(true);
      expect(saveButton(fixture).disabled).toBe(false);
      expect(component.hasChanges).toBe(true);
    });

    it("keeps a typed value while another parameter is typed", async () => {
      await typeInto(fixture, "required_p", "first");
      await typeInto(fixture, "optional_p", "second");
      expect(component.smsModel().parameters).toEqual({ required_p: "first", optional_p: "second" });
    });

    it("clears a parameter through the clear button and marks it dirty", async () => {
      component.smsModel.update((m) => ({ ...m, parameters: { ...m.parameters, optional_p: "x" } }));
      await flush(fixture);
      expect(component.smsForm.parameters["optional_p"]().dirty()).toBe(false);
      clearButtonOf(fixture, "optional_p").click();
      await flush(fixture);
      expect(component.smsModel().parameters["optional_p"]).toBe("");
      expect(component.smsForm.parameters["optional_p"]().dirty()).toBe(true);
    });

    it("keeps the typed values when the provider list reloads", async () => {
      await typeInto(fixture, "required_p", "typed");
      await typeInto(fixture, "optional_p", "also typed");

      setProviders({ ...requiredProviders });
      await flush(fixture);

      expect(component.smsModel().parameters).toEqual({ required_p: "typed", optional_p: "also typed" });
      expect(component.smsForm.parameters["required_p"]().dirty()).toBe(true);
      expect(component.hasChanges).toBe(true);
    });

    it("adds the fields of a parameter that a reloaded provider list introduces", async () => {
      await typeInto(fixture, "required_p", "typed");

      setProviders({
        mod1: {
          parameters: {
            required_p: { description: "d", required: true },
            added_p: { description: "new" }
          }
        }
      });
      await flush(fixture);

      expect(component.smsModel().parameters).toEqual({ required_p: "typed", added_p: "" });
      expect(controlOf(fixture, "added_p")).toBeTruthy();
    });

    it("replaces the parameters and resets their state when another provider is selected", async () => {
      setProviders({
        ...requiredProviders,
        mod2: { parameters: { other_p: { description: "o" }, required_p: { description: "d", required: true } } }
      });
      await flush(fixture);
      await typeInto(fixture, "required_p", "typed");

      await pickOption(fixture, "Provider Module", "mod2");

      expect(component.smsModel().providermodule).toBe("mod2");
      expect(component.smsModel().parameters).toEqual({ other_p: "", required_p: "" });
      expect(component.smsForm.parameters["required_p"]().dirty()).toBe(false);
      expect(component.smsForm.parameters["required_p"]().touched()).toBe(false);
      expect(component.smsForm.providermodule().dirty()).toBe(true);
      expect(component.hasChanges).toBe(true);
    });

    it("drops the parameter section when the selected module is not a known provider", async () => {
      component.smsModel.update((m) => ({ ...m, providermodule: "unknown.module" }));
      await flush(fixture);
      expect(component.selectedProvider()).toBeUndefined();
      expect(component.smsModel().parameters).toEqual({});
      expect(fixture.nativeElement.querySelector(".parameters-form")).toBeNull();
    });
  });

  describe("parameter controls", () => {
    beforeEach(async () => {
      await setup({
        providers: {
          mod1: {
            parameters: {
              CHOICE: { description: "pick", values: ["a", "b"], required: true },
              BODY: { description: "text", type: "text" },
              PLAIN: { description: "plain" }
            }
          }
        }
      });
      component.smsModel.update((m) => ({ ...m, name: "gw", providermodule: "mod1" }));
      await flush(fixture);
    });

    it("renders a select, a textarea and an input for the parameter kinds", () => {
      expect(formFieldOf(fixture, "CHOICE").querySelector("mat-select")).toBeTruthy();
      expect(formFieldOf(fixture, "BODY").querySelector("textarea")).toBeTruthy();
      expect(formFieldOf(fixture, "PLAIN").querySelector("input")).toBeTruthy();
    });

    it("writes the picked select option to the model", async () => {
      expect(component.canSave).toBe(false);
      await pickOption(fixture, "CHOICE", "b");
      expect(component.smsModel().parameters["CHOICE"]).toBe("b");
      expect(component.smsForm.parameters["CHOICE"]().dirty()).toBe(true);
      expect(component.canSave).toBe(true);
    });

    it("shows a model value in the select", async () => {
      component.smsModel.update((m) => ({ ...m, parameters: { ...m.parameters, CHOICE: "a" } }));
      await flush(fixture);
      expect(formFieldOf(fixture, "CHOICE").querySelector(".mat-mdc-select-value-text")?.textContent).toContain("a");
    });

    it("writes the textarea content to the model", async () => {
      await typeInto(fixture, "BODY", "line1\nline2");
      expect(component.smsModel().parameters["BODY"]).toBe("line1\nline2");
    });
  });

  describe("custom options and headers", () => {
    beforeEach(async () => {
      await setup({ providers: requiredProviders });
      component.smsModel.update((m) => ({ ...m, providermodule: "mod1" }));
      await flush(fixture);
    });

    it("hasChanges should be true when only description changes", async () => {
      expect(component.hasChanges).toBe(false);
      await typeInto(fixture, "Description", "updated");
      expect(component.hasChanges).toBe(true);
    });

    it("hasChanges should be true when new option secret checkbox is toggled", async () => {
      expect(component.hasChanges).toBe(false);
      (footerRow(fixture, 0).querySelector("mat-checkbox input") as HTMLInputElement).click();
      await flush(fixture);
      expect(component.optionDraft().secret).toBe(true);
      expect(component.hasChanges).toBe(true);
    });

    it("hasChanges should be true when new header secret checkbox is toggled", async () => {
      expect(component.hasChanges).toBe(false);
      (footerRow(fixture, 1).querySelector("mat-checkbox input") as HTMLInputElement).click();
      await flush(fixture);
      expect(component.headerDraft().secret).toBe(true);
      expect(component.hasChanges).toBe(true);
    });

    it("hasChanges should be true when only a draft value is typed", async () => {
      await typeInto(fixture, "Value", "v");
      expect(component.optionDraft().value).toBe("v");
      expect(component.hasChanges).toBe(true);
    });

    it("keeps the Add buttons disabled until the draft key is typed", async () => {
      expect(addButtonOf(fixture, 0).disabled).toBe(true);
      expect(addButtonOf(fixture, 1).disabled).toBe(true);
      expect(component.optionDraftForm().valid()).toBe(false);
      expect(component.headerDraftForm().valid()).toBe(false);

      await typeInto(fixture, "Option Name", "k1");
      expect(addButtonOf(fixture, 0).disabled).toBe(false);
      expect(addButtonOf(fixture, 1).disabled).toBe(true);

      await typeInto(fixture, "Header Name", "h1");
      expect(addButtonOf(fixture, 1).disabled).toBe(false);
    });

    it("shows the required error of a draft key once touched", async () => {
      controlOf(fixture, "Option Name").dispatchEvent(new Event("blur"));
      controlOf(fixture, "Header Name").dispatchEvent(new Event("blur"));
      await flush(fixture);
      expect(formFieldOf(fixture, "Option Name").textContent).toContain("Option name is required");
      expect(formFieldOf(fixture, "Header Name").textContent).toContain("Header name is required");
    });

    it("adds a typed option through the Add button and resets the draft", async () => {
      await typeInto(fixture, "Option Name", "k1");
      await typeInto(fixture, "Value", "v1");
      addButtonOf(fixture, 0).click();
      await flush(fixture);
      expect(component.customOptions).toEqual({ k1: "v1" });
      expect(component.optionDraft()).toEqual({ key: "", value: "", secret: false });
      expect(component.optionDraftForm().dirty()).toBe(false);
      expect(controlOf(fixture, "Option Name").value).toBe("");
    });

    it("adds a typed header through the Add button and resets the draft", async () => {
      await typeInto(fixture, "Header Name", "h1");
      const valueInput = footerRow(fixture, 1).querySelectorAll("input")[1] as HTMLInputElement;
      valueInput.value = "hv1";
      valueInput.dispatchEvent(new Event("input"));
      await flush(fixture);
      addButtonOf(fixture, 1).click();
      await flush(fixture);
      expect(component.customHeaders).toEqual({ h1: "hv1" });
      expect(component.headerDraft()).toEqual({ key: "", value: "", secret: false });
    });

    it("clears the draft key and value through the clear buttons", async () => {
      await typeInto(fixture, "Option Name", "k1");
      clearButtonOf(fixture, "Option Name").click();
      await flush(fixture);
      expect(component.optionDraft().key).toBe("");

      await typeInto(fixture, "Header Name", "h1");
      clearButtonOf(fixture, "Header Name").click();
      await flush(fixture);
      expect(component.headerDraft().key).toBe("");
    });

    it("addOption should record the secret flag and reset the draft secret", () => {
      component.optionDraft.set({ key: "k1", value: "v1", secret: true });
      component.addOption();
      expect(component.customOptions).toEqual({ k1: "v1" });
      expect(component.optionSecrets).toEqual({ k1: true });
      expect(component.optionDraft().secret).toBe(false);
    });

    it("addOption should not mark a non-secret option as secret", () => {
      component.optionDraft.set({ key: "k1", value: "v1", secret: false });
      component.addOption();
      expect(component.optionSecrets).toEqual({});
    });

    it("addOption should clear an earlier secret flag of the same key", () => {
      component.optionSecrets = { k1: true };
      component.optionDraft.set({ key: "k1", value: "v1", secret: false });
      component.addOption();
      expect(component.optionSecrets).toEqual({});
    });

    it("addOption should not add when key is empty", () => {
      component.optionDraft.set({ key: "", value: "v1", secret: true });
      component.addOption();
      expect(component.customOptions).toEqual({});
      expect(component.optionDraft().value).toBe("v1");
    });

    it("addHeader should record the secret flag and reset the draft secret", () => {
      component.headerDraft.set({ key: "h1", value: "hv1", secret: true });
      component.addHeader();
      expect(component.customHeaders).toEqual({ h1: "hv1" });
      expect(component.headerSecrets).toEqual({ h1: true });
      expect(component.headerDraft().secret).toBe(false);
    });

    it("addHeader should not add when key is empty", () => {
      component.addHeader();
      expect(component.customHeaders).toEqual({});
    });

    it("deleteOption should remove the option and its secret flag", () => {
      component.customOptions = { k1: "v1", k2: "v2" };
      component.optionSecrets = { k1: true, k2: true };
      component.deleteOption("k1");
      expect(component.customOptions).toEqual({ k2: "v2" });
      expect(component.optionSecrets).toEqual({ k2: true });
    });

    it("deleteHeader should remove the header and its secret flag", () => {
      component.customHeaders = { h1: "hv1", h2: "hv2" };
      component.headerSecrets = { h1: true, h2: true };
      component.deleteHeader("h1");
      expect(component.customHeaders).toEqual({ h2: "hv2" });
      expect(component.headerSecrets).toEqual({ h2: true });
    });

    it("toggleOptionSecret should flip the secret flag for a key", () => {
      expect(component.optionSecrets["k1"]).toBeFalsy();
      component.toggleOptionSecret("k1");
      expect(component.optionSecrets["k1"]).toBe(true);
      component.toggleOptionSecret("k1");
      expect(component.optionSecrets["k1"]).toBe(false);
    });

    it("toggleHeaderSecret should flip the secret flag for a key", () => {
      expect(component.headerSecrets["h1"]).toBeFalsy();
      component.toggleHeaderSecret("h1");
      expect(component.headerSecrets["h1"]).toBe(true);
      component.toggleHeaderSecret("h1");
      expect(component.headerSecrets["h1"]).toBe(false);
    });

    it("optionRows should return sorted entries with the secret flag", () => {
      component.customOptions = { z: "1", a: "2" };
      component.optionSecrets = { a: true };
      expect(component.optionRows).toEqual([
        { key: "a", value: "2", secret: true },
        { key: "z", value: "1", secret: false }
      ]);
    });

    it("headerRows should return sorted entries with the secret flag", () => {
      component.customHeaders = { b: "1", a: "2" };
      component.headerSecrets = { b: true };
      expect(component.headerRows).toEqual([
        { key: "a", value: "2", secret: false },
        { key: "b", value: "1", secret: true }
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

  describe("save", () => {
    beforeEach(async () => setup({ providers: requiredProviders }));

    const payloadOfFirstCall = () => {
      const calls = smsGatewayServiceMock.postSmsGateway.mock.calls as unknown as [Record<string, unknown>][];
      return calls[0][0];
    };

    it("should include a draft option row even if Add was not clicked", async () => {
      component.smsModel.set({ name: "gw", providermodule: "mod1", description: "d", parameters: {} });
      component.optionDraft.set({ key: "draftOpt", value: "draftVal", secret: true });

      await component.save();

      expect(payloadOfFirstCall()["option.draftOpt"]).toBe("draftVal");
      expect(payloadOfFirstCall()["secret.option.draftOpt"]).toBe(1);
    });

    it("should include a draft header row even if Add was not clicked", async () => {
      component.smsModel.set({ name: "gw", providermodule: "mod1", description: "d", parameters: {} });
      component.headerDraft.set({ key: "X-Draft", value: "draftVal", secret: false });

      await component.save();

      expect(payloadOfFirstCall()["header.X-Draft"]).toBe("draftVal");
      expect(payloadOfFirstCall()["secret.header.X-Draft"]).toBe(0);
    });

    it("should ignore a draft row without a key", async () => {
      component.smsModel.set({ name: "gw", providermodule: "mod1", description: "d", parameters: {} });
      component.optionDraft.set({ key: "", value: "orphan", secret: false });

      await component.save();

      expect(Object.keys(payloadOfFirstCall()).filter((k) => k.startsWith("option."))).toEqual([]);
    });

    it("should include option.* and header.* entries in the payload", async () => {
      component.smsModel.set({
        name: "gw",
        providermodule: "mod1",
        description: "d",
        parameters: { required_p: "v1", optional_p: "" }
      });
      component.customOptions = { extra: "ext-val" };
      component.customHeaders = { "X-Test": "header-val" };

      await component.save();

      expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "gw",
          module: "mod1",
          description: "d",
          "option.required_p": "v1",
          "option.optional_p": "",
          "option.extra": "ext-val",
          "header.X-Test": "header-val"
        })
      );
    });

    it("should return false and touch every field when the form is invalid", async () => {
      component.smsModel.set({ name: "", providermodule: "", description: "", parameters: {} });
      const result = await component.save();
      expect(result).toBe(false);
      expect(smsGatewayServiceMock.postSmsGateway).not.toHaveBeenCalled();
      expect(component.smsForm.name().touched()).toBe(true);
      expect(component.smsForm.providermodule().touched()).toBe(true);
    });

    it("should send secret.option.* and secret.header.* flags for marked custom entries", async () => {
      component.smsModel.set({
        name: "gw",
        providermodule: "mod1",
        description: "d",
        parameters: { required_p: "v1", optional_p: "" }
      });
      component.customOptions = { secretOpt: "s1", plainOpt: "p1v" };
      component.optionSecrets = { secretOpt: true };
      component.customHeaders = { "X-Secret": "h1", "X-Plain": "h2" };
      component.headerSecrets = { "X-Secret": true };

      await component.save();

      expect(payloadOfFirstCall()["secret.option.secretOpt"]).toBe(1);
      expect(payloadOfFirstCall()["secret.option.plainOpt"]).toBe(0);
      expect(payloadOfFirstCall()["secret.header.X-Secret"]).toBe(1);
      expect(payloadOfFirstCall()["secret.header.X-Plain"]).toBe(0);
    });

    it("should send secret.option.* for provider parameters declared secret", async () => {
      setProviders({
        mod1: {
          parameters: {
            p1: { description: "d" },
            pwd: { description: "secret param", secret: true }
          }
        }
      });
      component.smsModel.set({ name: "gw", providermodule: "mod1", description: "d", parameters: {} });
      component.onProviderChange("mod1");
      component.smsModel.update((m) => ({ ...m, parameters: { p1: "v1", pwd: "topsecret" } }));

      await component.save();

      expect(payloadOfFirstCall()["option.pwd"]).toBe("topsecret");
      expect(payloadOfFirstCall()["secret.option.pwd"]).toBe(1);
      expect(payloadOfFirstCall()["secret.option.p1"]).toBeUndefined();
    });

    it("save in edit mode should include the gateway id in the payload", async () => {
      component.isEditMode.set(true);
      internals(component).data = {
        id: 99,
        name: "edit-gw",
        providermodule: "mod1",
        options: {},
        headers: {}
      };
      component.smsModel.set({ name: "edit-gw", providermodule: "mod1", description: "x", parameters: {} });

      await component.save();

      expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalledWith(expect.objectContaining({ id: 99 }));
    });
  });

  describe("onProviderChange", () => {
    beforeEach(async () => setup());

    it("fills custom options from data not matching provider parameters", () => {
      setProviders({ mod1: { parameters: { p1: { description: "d", required: true } } } });
      component.isEditMode.set(true);
      internals(component).data = {
        id: 42,
        name: "edit-gw",
        providermodule: "mod1",
        options: { p1: "fromData", extra: "custom-val" },
        headers: { "X-Auth": "secret" }
      };
      component.smsModel.update((m) => ({ ...m, providermodule: "mod1" }));

      component.onProviderChange("mod1");

      expect(component.smsModel().parameters["p1"]).toBe("fromData");
      expect(component.customOptions).toEqual({ extra: "custom-val" });
      expect(component.customHeaders).toEqual({ "X-Auth": "secret" });
    });

    it("should restore secret flags from secret_options/secret_headers in edit mode", () => {
      setProviders({ mod1: { parameters: { p1: { description: "d" } } } });
      component.isEditMode.set(true);
      internals(component).data = {
        id: 7,
        name: "edit-gw",
        providermodule: "mod1",
        options: { p1: "fromData", extraSecret: "__CENSORED__", extraPlain: "v" },
        headers: { "X-Auth": "__CENSORED__", "X-Plain": "v" },
        secret_options: ["extraSecret"],
        secret_headers: ["X-Auth"]
      };
      component.smsModel.update((m) => ({ ...m, providermodule: "mod1" }));

      component.onProviderChange("mod1");

      expect(component.optionSecrets).toEqual({ extraSecret: true });
      expect(component.headerSecrets).toEqual({ "X-Auth": true });
    });

    it("should not put provider-parameter keys into optionSecrets", () => {
      setProviders({ mod1: { parameters: { p1: { description: "d" } } } });
      component.isEditMode.set(true);
      internals(component).data = {
        id: 8,
        name: "edit-gw",
        providermodule: "mod1",
        options: { p1: "__CENSORED__" },
        headers: {},
        // p1 is a provider parameter; it must be excluded from custom optionSecrets
        secret_options: ["p1"]
      };
      component.smsModel.update((m) => ({ ...m, providermodule: "mod1" }));

      component.onProviderChange("mod1");

      expect(component.optionSecrets).toEqual({});
    });

    it("keeps the current parameter values when the same module is applied again", () => {
      component.smsModel.update((m) => ({ ...m, providermodule: "mod1" }));
      component.onProviderChange("mod1");
      component.smsModel.update((m) => ({ ...m, parameters: { p1: "typed" } }));

      component.onProviderChange("mod1");

      expect(component.smsModel().parameters).toEqual({ p1: "typed" });
    });
  });

  describe("providerEntries / parameterEntries", () => {
    beforeEach(async () => setup());

    it("providerEntries should map current providers to entries", () => {
      setProviders({ modA: { parameters: {} }, modB: { parameters: {} } });
      const entries = component.providerEntries();
      expect(entries.map((e) => e.key).sort()).toEqual(["modA", "modB"]);
    });

    it("parameterEntries should return entries for currently selected provider", () => {
      component.selectedProvider.set({ parameters: { p1: { description: "d" } as SmsProviderParameter } });
      const entries = component.parameterEntries();
      expect(entries).toEqual([{ key: "p1", value: { description: "d" } }]);
    });

    it("parameterEntries should return empty array when no provider selected", () => {
      component.selectedProvider.set(undefined);
      expect(component.parameterEntries()).toEqual([]);
    });
  });

  describe("edit mode", () => {
    beforeEach(async () => setup({ name: "edit-gw", gateways: [existingGateway], providers: requiredProviders }));

    it("loads the stored gateway into the form without marking it dirty", () => {
      expect(component.isEditMode()).toBe(true);
      expect(component.smsModel()).toEqual({
        name: "edit-gw",
        providermodule: "mod1",
        description: "stored",
        parameters: { required_p: "stored-required", optional_p: "stored-optional" }
      });
      expect(component.customOptions).toEqual({ extra: "custom-val" });
      expect(component.customHeaders).toEqual({ "X-Auth": "token" });
      expect(component.optionSecrets).toEqual({ extra: true });
      expect(component.smsForm().dirty()).toBe(false);
      expect(component.hasChanges).toBe(false);
      expect(component.canSave).toBe(true);
    });

    it("disables the name field", () => {
      expect(component.smsForm.name().disabled()).toBe(true);
      expect(controlOf(fixture, "Name").disabled).toBe(true);
    });

    it("shows the stored parameter values in the inputs", () => {
      expect(controlOf(fixture, "required_p").value).toBe("stored-required");
      expect(controlOf(fixture, "optional_p").value).toBe("stored-optional");
    });

    it("blocks saving when a required parameter is emptied and reports it", async () => {
      clearButtonOf(fixture, "required_p").click();
      controlOf(fixture, "required_p").dispatchEvent(new Event("blur"));
      await flush(fixture);
      expect(component.smsModel().parameters["required_p"]).toBe("");
      expect(component.hasChanges).toBe(true);
      expect(component.canSave).toBe(false);
      expect(saveButton(fixture).disabled).toBe(true);
      expect(formFieldOf(fixture, "required_p").textContent).toContain("required_p is required");
    });

    it("keeps typed values and rows when the provider list reloads", async () => {
      await typeInto(fixture, "optional_p", "typed");
      component.deleteOption("extra");

      setProviders({ ...requiredProviders });
      await flush(fixture);

      expect(component.smsModel().parameters["optional_p"]).toBe("typed");
      expect(component.customOptions).toEqual({});
      expect(component.hasChanges).toBe(true);
    });

    it("keeps an added option row when the gateway list reloads", async () => {
      await typeInto(fixture, "Option Name", "newopt");
      addButtonOf(fixture, 0).click();
      await flush(fixture);

      smsGatewayServiceMock.smsGateways.set([{ ...existingGateway }]);
      await flush(fixture);

      expect(component.customOptions).toEqual({ extra: "custom-val", newopt: "" });
    });

    it("keeps a typed draft row when the gateway list reloads", async () => {
      await typeInto(fixture, "Header Name", "X-Draft");

      smsGatewayServiceMock.smsGateways.set([{ ...existingGateway }]);
      await flush(fixture);

      expect(component.headerDraft().key).toBe("X-Draft");
    });

    it("keeps an edit when the gateway list reloads", async () => {
      await typeInto(fixture, "optional_p", "typed");

      smsGatewayServiceMock.smsGateways.set([
        { ...existingGateway, options: { ...existingGateway.options, optional_p: "server-changed" } }
      ]);
      await flush(fixture);

      expect(component.smsModel().parameters["optional_p"]).toBe("typed");
    });

    it("re-initializes from a reloaded gateway list while the form is pristine", async () => {
      smsGatewayServiceMock.smsGateways.set([
        {
          ...existingGateway,
          description: "reloaded",
          options: { ...existingGateway.options, optional_p: "server-changed" },
          headers: { "X-Auth": "new-token" }
        }
      ]);
      await flush(fixture);

      expect(component.smsModel().description).toBe("reloaded");
      expect(component.smsModel().parameters["optional_p"]).toBe("server-changed");
      expect(component.customHeaders).toEqual({ "X-Auth": "new-token" });
      expect(component.hasChanges).toBe(false);
    });

    it("saves the edited parameters together with the gateway id", async () => {
      await typeInto(fixture, "optional_p", "typed");

      await component.save();

      expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 5,
          name: "edit-gw",
          module: "mod1",
          "option.required_p": "stored-required",
          "option.optional_p": "typed",
          "option.extra": "custom-val",
          "secret.option.extra": 1,
          "header.X-Auth": "token"
        })
      );
    });
  });

  describe("edit mode with a late provider list", () => {
    it("fills the parameters once the providers arrive", async () => {
      await setup({ name: "edit-gw", gateways: [existingGateway], providers: {} });
      expect(component.smsModel().parameters).toEqual({});
      expect(component.selectedProvider()).toBeUndefined();

      setProviders(requiredProviders);
      await flush(fixture);

      expect(component.smsModel().parameters).toEqual({
        required_p: "stored-required",
        optional_p: "stored-optional"
      });
      expect(component.hasChanges).toBe(false);
    });

    it("fills the form once the gateway list arrives", async () => {
      await setup({ name: "edit-gw", providers: requiredProviders });
      expect(component.smsModel().name).toBe("");

      smsGatewayServiceMock.smsGateways.set([existingGateway]);
      await flush(fixture);

      expect(component.smsModel().name).toBe("edit-gw");
      expect(component.smsModel().parameters["required_p"]).toBe("stored-required");
      expect(component.hasChanges).toBe(false);
    });
  });

  describe("deleteGateway", () => {
    let dialog: MockDialogService;
    let pending: MockPendingChangesService;
    let service: MockSmsGatewayService;
    let navigateSpy: jest.SpyInstance;

    beforeEach(async () => {
      await setup();
      dialog = TestBed.inject(DialogService) as unknown as MockDialogService;
      pending = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
      service = TestBed.inject(SmsGatewayService) as unknown as MockSmsGatewayService;
      navigateSpy = jest.spyOn(TestBed.inject(Router), "navigateByUrl").mockResolvedValue(true);
      component["gatewayName"] = "sms-gateway";
    });

    it("does nothing without an identifier", async () => {
      component["gatewayName"] = null;
      await component.deleteGateway();
      expect(dialog.confirmDelete).not.toHaveBeenCalled();
      expect(service.deleteSmsGateway).not.toHaveBeenCalled();
    });

    it("does not delete when the confirmation is cancelled", async () => {
      dialog.confirmDelete.mockResolvedValue(false);
      await component.deleteGateway();
      expect(service.deleteSmsGateway).not.toHaveBeenCalled();
      expect(navigateSpy).not.toHaveBeenCalled();
    });

    it("deletes after confirmation and navigates back to the list", async () => {
      await component.deleteGateway();
      expect(dialog.confirmDelete).toHaveBeenCalledWith(expect.objectContaining({ items: ["sms-gateway"] }));
      expect(service.deleteSmsGateway).toHaveBeenCalledWith("sms-gateway");
      expect(pending.clearAllRegistrations).toHaveBeenCalled();
      expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    });

    it("stays on the page when the deletion fails", async () => {
      service.deleteSmsGateway.mockRejectedValue(new Error("delete failed"));
      await component.deleteGateway();
      expect(pending.clearAllRegistrations).not.toHaveBeenCalled();
      expect(navigateSpy).not.toHaveBeenCalled();
    });
  });
});
