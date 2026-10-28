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
import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { form, maxLength } from "@angular/forms/signals";
import { MatExpansionPanel } from "@angular/material/expansion";
import { By } from "@angular/platform-browser";
import {
  ContainerRegistrationConfigComponent,
  ContainerRegistrationModel,
  emptyRegistration,
  registrationRules
} from "@components/container/container-registration/container-registration-config/container-registration-config.component";
import { ContainerService, ContainerTemplate } from "@services/container/container.service";
import { TokenService } from "@services/token/token.service";
import { AuthService } from "@services/auth/auth.service";
import { MockContainerService, MockTokenService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { ContainerCreateFormComponent } from "./container-create-form.component";

const template = (name: string): ContainerTemplate => ({
  container_type: "smartphone",
  default: false,
  name,
  template_options: { tokens: [] }
});
const EMPTY_TEMPLATE = template("");

@Component({
  imports: [ContainerCreateFormComponent],
  template: `
    <app-container-create-form
      [authService]="authService"
      [availableTokenTypes]="[]"
      [containerService]="containerService"
      [descriptionField]="createForm.description"
      [generateQRCode]="generateQRCode()"
      (generateQRCodeChange)="generateQRCode.set($event)"
      [registration]="createForm.registration"
      [selectedTemplate]="selectedTemplate()"
      (selectedTemplateChange)="selectedTemplate.set($event)"
      [showRegistration]="showRegistration()"
      [templateOptions]="templateOptions()"
      [tokenService]="tokenService"
      (clearTemplate)="clearTemplate()"
      (templateChange)="templateChange($event)" />
  `
})
class HostComponent {
  authService = TestBed.inject(AuthService) as unknown as MockAuthService;
  containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
  tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;

  model = signal<{ description: string; registration: ContainerRegistrationModel }>({
    description: "",
    registration: emptyRegistration()
  });
  createForm = form(this.model, (f) => {
    maxLength(f.description, 80);
    registrationRules(f.registration, {
      value: () => this.model().registration,
      active: () => this.generateQRCode(),
      hasOwner: () => true
    });
  });
  generateQRCode = signal(false);
  selectedTemplate = signal<ContainerTemplate>(EMPTY_TEMPLATE);
  templateOptions = signal<ContainerTemplate[]>([template("first"), template("second")]);
  showRegistration = signal(true);
  clearTemplate = jest.fn();
  templateChange = jest.fn();
}

describe("ContainerCreateFormComponent", () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;
  let authService: MockAuthService;
  let containerService: MockContainerService;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const el = () => fixture.nativeElement as HTMLElement;
  const descriptionInput = () => el().querySelector("textarea") as HTMLTextAreaElement;
  const qrCheckbox = () => el().querySelector("mat-checkbox input") as HTMLInputElement;
  const clearButton = () => el().querySelector("app-clear-button");
  const pickTemplate = async (index: number) => {
    (el().querySelector("mat-select .mat-mdc-select-trigger") as HTMLElement).click();
    await flush();
    (document.querySelectorAll("mat-option")[index] as HTMLElement).click();
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    authService.actionAllowed.mockReturnValue(true);
    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    containerService.selectedContainerType.set({
      containerType: "smartphone",
      description: "",
      token_types: ["hotp", "totp"]
    });
    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    await flush();
  });

  afterEach(() => {
    document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
  });

  describe("supported token types", () => {
    const hint = () => el().querySelector(".container-type-hint")?.textContent?.replace(/\s+/g, " ").trim();

    it("lists the token types of the selected container type", () => {
      expect(hint()).toContain("hotp, totp");
    });

    it("shows the only token type of a single-type container", async () => {
      containerService.selectedContainerType.set({ containerType: "yubikey", description: "", token_types: ["hotp"] });
      await flush();
      expect(hint()).toContain("hotp");
      expect(hint()).not.toContain("All");
    });

    it("shows All when every token type is supported", async () => {
      containerService.selectedContainerType.set({
        containerType: "generic",
        description: "",
        token_types: ["hotp", "totp", "push"]
      });
      await flush();
      expect(hint()).toContain("All");
    });
  });

  describe("description", () => {
    it("writes typed text to the model and marks the field dirty", async () => {
      descriptionInput().value = "my container";
      descriptionInput().dispatchEvent(new Event("input"));
      await flush();
      expect(host.model().description).toBe("my container");
      expect(host.createForm.description().dirty()).toBe(true);
    });

    it("shows a description set in the model", async () => {
      host.model.update((model) => ({ ...model, description: "preset" }));
      await flush();
      expect(descriptionInput().value).toBe("preset");
    });

    it("limits the length to the rule of the form", () => {
      expect(descriptionInput().maxLength).toBe(80);
    });
  });

  describe("template", () => {
    it("hides the template section without the right to list templates", async () => {
      fixture.destroy();
      authService.actionAllowed.mockReturnValue(false);
      fixture = TestBed.createComponent(HostComponent);
      await flush();
      expect(el().querySelector("mat-select")).toBeNull();
    });

    it("shows the template select with the right to list templates", () => {
      expect(el().querySelector("mat-select")).not.toBeNull();
    });

    it("writes the picked template to the selected template", async () => {
      await pickTemplate(1);
      expect(host.selectedTemplate().name).toBe("second");
    });

    it("selects the option of a template that is equal by name", async () => {
      host.selectedTemplate.set(template("first"));
      await flush();
      await pickTemplate(0);
      expect(host.selectedTemplate().name).toBe("first");
      const select = fixture.debugElement.query(By.css("mat-select")).componentInstance;
      expect(select.compareWith(template("a"), template("a"))).toBe(true);
      expect(select.compareWith(template("a"), template("b"))).toBe(false);
      expect(select.compareWith(null, null)).toBe(true);
    });

    it("hides the clear button while no template is selected", () => {
      expect(clearButton()).toBeNull();
    });

    it("shows the clear button once a template is selected and emits clearTemplate when it is clicked", async () => {
      host.selectedTemplate.set(template("first"));
      await flush();
      expect(clearButton()).not.toBeNull();
      (clearButton()?.querySelector("button") as HTMLButtonElement).click();
      expect(host.clearTemplate).toHaveBeenCalledTimes(1);
    });

    it("forwards a template change of the token editor", async () => {
      host.selectedTemplate.set(template("first"));
      await flush();
      const edited = template("edited");
      const body = fixture.debugElement.query(By.css("app-container-template-edit-body"));
      body.triggerEventHandler("templateChange", edited);
      expect(host.templateChange).toHaveBeenCalledWith(edited);
    });
  });

  describe("registration", () => {
    it("is hidden when registration is not shown", async () => {
      host.showRegistration.set(false);
      await flush();
      expect(el().querySelector("mat-checkbox")).toBeNull();
      expect(fixture.debugElement.query(By.directive(ContainerRegistrationConfigComponent))).toBeNull();
    });

    it("shows the registration settings when registration is shown", () => {
      expect(fixture.debugElement.query(By.directive(ContainerRegistrationConfigComponent))).not.toBeNull();
    });

    it("writes the checkbox to generateQRCode", async () => {
      expect(host.generateQRCode()).toBe(false);
      qrCheckbox().click();
      await flush();
      expect(host.generateQRCode()).toBe(true);
    });

    it("shows generateQRCode as checked", async () => {
      host.generateQRCode.set(true);
      await flush();
      expect(qrCheckbox().checked).toBe(true);
    });

    it("disables the settings panel while no QR code is generated", async () => {
      const panel = () =>
        fixture.debugElement.query(By.css("mat-accordion mat-expansion-panel")).componentInstance as MatExpansionPanel;
      expect(panel().disabled).toBe(true);
      host.generateQRCode.set(true);
      await flush();
      expect(panel().disabled).toBe(false);
    });

    it("passes the registration fields to the settings", async () => {
      host.model.update((model) => ({ ...model, registration: { ...model.registration, prompt: "Prompt?" } }));
      await flush();
      expect((el().querySelector("mat-expansion-panel textarea") as HTMLTextAreaElement).value).toBe("Prompt?");
    });
  });
});
