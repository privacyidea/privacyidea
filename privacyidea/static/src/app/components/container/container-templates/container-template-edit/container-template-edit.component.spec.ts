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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ROUTE_PATHS } from "../../../../route_paths";
import { AuthService } from "../../../../services/auth/auth.service";
import { ContentService } from "../../../../services/content/content.service";
import { NotificationService } from "../../../../services/notification/notification.service";
import { ContainerService } from "../../../../services/container/container.service";
import { TokenEnrollmentPayload } from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";
import { ContainerTemplate } from "../../../../services/container/container.service";
import { ERR } from "../../../../utils/form-rules.utils";
import { MockContainerTemplateService } from "../../../../../testing/mock-services/mock-container-template-service";
import { TokenService } from "../../../../services/token/token.service";
import { SystemService } from "../../../../services/system/system.service";
import {
  MockAuthService,
  MockContainerService,
  MockContentService,
  MockNotificationService,
  MockSystemService,
  MockTokenService
} from "../../../../../testing/mock-services";
import { ContainerTemplateEditComponent } from "./container-template-edit.component";

describe("ContainerTemplateEditComponent", () => {
  let component: ContainerTemplateEditComponent;
  let fixture: ComponentFixture<ContainerTemplateEditComponent>;
  let serviceMock: MockContainerTemplateService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateEditComponent],
      providers: [
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateEditComponent);
    component = fixture.componentInstance;
    serviceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("editTemplate merges partial updates into the template signal", () => {
    component.editTemplate({ name: "NewName" });
    expect(component.template().name).toBe("NewName");

    component.editTemplate({ container_type: "smartphone" });
    expect(component.template().container_type).toBe("smartphone");
    expect(component.template().name).toBe("NewName");
  });

  it("tokens computed returns template_options.tokens", () => {
    expect(component.tokens()).toEqual([]);

    component.editTemplate({
      template_options: { tokens: [{ type: "hotp" } as unknown as TokenEnrollmentPayload] }
    });
    expect(component.tokens().length).toBe(1);
    expect((component.tokens()[0] as Partial<TokenEnrollmentPayload>).type).toBe("hotp");
  });

  describe("template name rules", () => {
    const existing = (name: string): ContainerTemplate => ({
      name,
      container_type: "generic",
      default: false,
      template_options: { tokens: [] }
    });
    const kinds = () =>
      component.form
        .name()
        .errors()
        .map((e) => e.kind);

    it("requires a name", () => {
      expect(kinds()).toEqual([ERR.required]);
    });

    it("accepts letters, digits, dots, dashes and underscores", () => {
      component.editTemplate({ name: "valid-Name_1.0" });
      expect(kinds()).toEqual([]);
    });

    it.each(["has space", "bad!", "   "])("rejects the name %p as an invalid pattern", (name) => {
      component.editTemplate({ name });
      expect(kinds()).toEqual([ERR.pattern]);
    });

    it("reports a name that an existing template already has", () => {
      serviceMock.templates.set([existing("Existing")]);
      component.editTemplate({ name: "Existing" });
      expect(kinds()).toEqual([ERR.nameTaken]);
    });

    it("accepts a unique name", () => {
      serviceMock.templates.set([existing("Other")]);
      component.editTemplate({ name: "UniqueNewName" });
      expect(kinds()).toEqual([]);
    });

    it("does not report the name the template was opened with", () => {
      fixture = TestBed.createComponent(ContainerTemplateEditComponent);
      component = fixture.componentInstance;
      serviceMock.templates.set([existing("Opened")]);
      fixture.componentRef.setInput("template", existing("Opened"));
      fixture.detectChanges();

      expect(kinds()).toEqual([]);
    });

    it("skips the rules while the name is read-only", () => {
      serviceMock.templates.set([existing("Taken")]);
      component.editTemplate({ name: "Taken" });
      fixture.componentRef.setInput("nameEditable", false);
      fixture.detectChanges();

      expect(component.form.name().readonly()).toBe(true);
      expect(kinds()).toEqual([]);
    });
  });

  describe("canSave", () => {
    const token = { type: "hotp" } as unknown as TokenEnrollmentPayload;
    const makeValid = () =>
      component.editTemplate({
        name: "Valid",
        container_type: "generic",
        template_options: { tokens: [token] }
      });

    it("is false for the initial empty template", () => {
      expect(component.canSave()).toBe(false);
    });

    it("is true for a template with a name, a container type and a token", () => {
      makeValid();
      expect(component.canSave()).toBe(true);
    });

    it("is false without a token", () => {
      makeValid();
      component.editTemplate({ template_options: { tokens: [] } });
      expect(component.canSave()).toBe(false);
      expect(
        component.form.template_options
          .tokens()
          .errors()
          .map((e) => e.kind)
      ).toEqual([ERR.required]);
    });

    it("is false without a container type, even while tokens disable the field", () => {
      makeValid();
      component.editTemplate({ container_type: "" });
      expect(component.form.container_type().disabled()).toBe(true);
      expect(component.canSave()).toBe(false);
    });

    it("requires a container type while no token is added", () => {
      expect(
        component.form
          .container_type()
          .errors()
          .map((e) => e.kind)
      ).toEqual([ERR.required]);
    });

    it("is false for an invalid name", () => {
      makeValid();
      component.editTemplate({ name: "bad name" });
      expect(component.canSave()).toBe(false);
    });

    it("is false when another template has the name", () => {
      makeValid();
      serviceMock.templates.set([
        { name: "Valid", container_type: "generic", default: false, template_options: { tokens: [] } }
      ]);
      expect(component.canSave()).toBe(false);
    });
  });

  describe("template card", () => {
    const nameInput = (): HTMLInputElement => fixture.nativeElement.querySelector('input[aria-label="Template Name"]');
    const errors = (): string[] =>
      Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map((e) =>
        (e as HTMLElement).textContent!.trim()
      );
    const type = (value: string): void => {
      nameInput().value = value;
      nameInput().dispatchEvent(new Event("input"));
      nameInput().dispatchEvent(new Event("blur"));
      fixture.detectChanges();
    };

    it("writes the typed name to the template and marks the name dirty", () => {
      type("Typed");

      expect(component.template().name).toBe("Typed");
      expect(component.form.name().dirty()).toBe(true);
    });

    it("shows the required error once the empty name is touched", () => {
      nameInput().dispatchEvent(new Event("blur"));
      fixture.detectChanges();

      expect(errors()).toEqual(["Template name is required"]);
    });

    it("shows the invalid-characters error", () => {
      type("bad name!");

      expect(errors()).toHaveLength(1);
      expect(errors()[0]).toContain("invalid characters");
    });

    it("shows the error for a name that is taken", () => {
      serviceMock.templates.set([
        { name: "Taken", container_type: "generic", default: false, template_options: { tokens: [] } }
      ]);
      type("Taken");

      expect(errors()).toEqual(["Another template with this name already exists."]);
    });

    it("shows no error for a valid name", () => {
      type("Fine");

      expect(errors()).toEqual([]);
    });

    it("makes the name input read-only while the name is not editable", () => {
      expect(nameInput().readOnly).toBe(false);

      fixture.componentRef.setInput("nameEditable", false);
      fixture.detectChanges();

      expect(nameInput().readOnly).toBe(true);
    });

    it("keeps the key presses of the name input from reaching the surrounding card", () => {
      const event = new KeyboardEvent("keydown", { key: "a", bubbles: true });
      const stop = jest.spyOn(event, "stopPropagation");
      nameInput().dispatchEvent(event);

      expect(stop).toHaveBeenCalled();
    });

    it("writes the default checkbox to the template", () => {
      const checkbox: HTMLInputElement = fixture.nativeElement.querySelector("mat-checkbox input");
      checkbox.click();
      fixture.detectChanges();

      expect(component.template().default).toBe(true);
      expect(component.form.default().dirty()).toBe(true);
      expect(checkbox.checked).toBe(true);
    });

    it("shows the default checkbox of a template that is the default", () => {
      component.editTemplate({ default: true });
      fixture.detectChanges();

      expect((fixture.nativeElement.querySelector("mat-checkbox input") as HTMLInputElement).checked).toBe(true);
    });
  });

  it("containerTypes returns service availableContainerTypes", () => {
    serviceMock.availableContainerTypes.set(["generic", "smartphone"]);
    expect(component.containerTypes()).toEqual(["generic", "smartphone"]);
  });

  it("containerTypesTitleCase title-cases each container type", () => {
    serviceMock.availableContainerTypes.set(["generic", "smartphone", "yubikey"]);
    expect(component.containerTypesTitleCase()).toEqual(["Generic", "Smartphone", "Yubikey"]);
  });

  it("availableTokenTypes delegates to service for the current container_type", () => {
    serviceMock.getTokenTypesForContainerType.mockReturnValue(["hotp", "totp"]);
    component.editTemplate({ container_type: "smartphone" });
    expect(component.availableTokenTypes()).toEqual(["hotp", "totp"]);
    expect(serviceMock.getTokenTypesForContainerType).toHaveBeenCalledWith("smartphone");
  });

  it("hasToken is false when no tokens are defined", () => {
    expect(component.hasToken()).toBe(false);
  });

  it("hasToken is true when tokens are present", () => {
    component.editTemplate({
      template_options: { tokens: [{ type: "hotp" } as unknown as TokenEnrollmentPayload] }
    });
    expect(component.hasToken()).toBe(true);
  });

  it("initTemplate is frozen to the first template value (linkedSignal previous caching)", () => {
    const initial = component.template();
    const initSnapshot = component.initTemplate();
    expect(initSnapshot).toEqual(initial);

    component.editTemplate({ name: "Changed" });
    expect(component.initTemplate()).toEqual(initial);
  });

  describe("container type toggle", () => {
    const radios = (): HTMLButtonElement[] =>
      Array.from(fixture.nativeElement.querySelectorAll("app-toggle-group [role=radio]"));
    const labels = (): string[] => radios().map((radio) => radio.textContent!.trim());
    const render = (): void => {
      serviceMock.availableContainerTypes.set(["generic", "smartphone"]);
      fixture.detectChanges();
    };

    it("containerTypeOptions puts the empty string for None before the container types", () => {
      serviceMock.availableContainerTypes.set(["generic", "smartphone"]);

      expect(component.containerTypeOptions()).toEqual(["", "generic", "smartphone"]);
    });

    it("containerTypeLabels names None first and title-cases the container types", () => {
      serviceMock.availableContainerTypes.set(["generic", "smartphone"]);

      expect(component.containerTypeLabels()).toEqual(["None", "Generic", "Smartphone"]);
    });

    it("renders None first, followed by the container types, and names the group", () => {
      render();

      expect(labels()).toEqual(["None", "Generic", "Smartphone"]);
      expect(fixture.nativeElement.querySelector("app-toggle-group [role=radiogroup]").getAttribute("aria-label")).toBe(
        "Container Type"
      );
    });

    it("marks None as selected for a template without a container type", () => {
      render();

      expect(radios()[0].getAttribute("aria-checked")).toBe("true");
    });

    it("sets the container type of the template when a type is selected", () => {
      render();

      radios()[2].click();
      fixture.detectChanges();

      expect(component.template().container_type).toBe("smartphone");
      expect(radios()[2].getAttribute("aria-checked")).toBe("true");
    });

    it("sets an empty container type, never undefined, when None is selected", () => {
      render();
      radios()[1].click();
      fixture.detectChanges();
      expect(component.template().container_type).toBe("generic");

      radios()[0].click();
      fixture.detectChanges();

      expect(component.template().container_type).toBe("");
      expect(component.template().container_type).not.toBeUndefined();
    });

    it("offers no token types for None and leaves the token list untouched", () => {
      render();
      serviceMock.getTokenTypesForContainerType.mockReturnValue([]);
      radios()[1].click();
      fixture.detectChanges();
      radios()[0].click();
      fixture.detectChanges();

      expect(serviceMock.getTokenTypesForContainerType).toHaveBeenLastCalledWith("");
      expect(component.availableTokenTypes()).toEqual([]);
      expect(component.template().template_options.tokens).toEqual([]);
    });

    it("keeps the group enabled while the template has no token", () => {
      render();

      expect(radios().every((radio) => !radio.disabled)).toBe(true);
    });

    it("disables the group, keeping the selection visible, while the template has a token", () => {
      render();
      component.editTemplate({
        container_type: "smartphone",
        template_options: { tokens: [{ type: "hotp" } as unknown as TokenEnrollmentPayload] }
      });
      fixture.detectChanges();

      expect(radios().every((radio) => radio.disabled)).toBe(true);
      expect(radios()[2].getAttribute("aria-checked")).toBe("true");

      radios()[1].click();
      fixture.detectChanges();
      expect(component.template().container_type).toBe("smartphone");
    });
  });
});

describe("ContainerTemplateEditComponent on the create route with the real template service", () => {
  it("reports a name that an existing template already has", async () => {
    TestBed.configureTestingModule({
      imports: [ContainerTemplateEditComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ContainerTemplateService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: TokenService, useClass: MockTokenService },
        { provide: SystemService, useClass: MockSystemService }
      ]
    });
    (TestBed.inject(AuthService) as unknown as MockAuthService).actionAllowed.mockReturnValue(true);
    (TestBed.inject(ContentService) as unknown as MockContentService).routeUrl.set(
      ROUTE_PATHS.CONTAINERS_TEMPLATES_CREATE
    );
    const httpMock = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(ContainerTemplateEditComponent);
    fixture.detectChanges();
    httpMock
      .match((req) => req.url.endsWith("/container/templates"))
      .forEach((req) =>
        req.flush({
          result: {
            value: { templates: [{ name: "Existing", container_type: "generic", template_options: { tokens: [] } }] }
          }
        })
      );
    httpMock
      .match((req) => req.url.endsWith("/container/template/tokentypes"))
      .forEach((req) => req.flush({ result: { value: {} } }));
    TestBed.tick();
    await Promise.resolve();

    fixture.componentInstance.editTemplate({ name: "Existing" });

    expect(
      fixture.componentInstance.form
        .name()
        .errors()
        .map((e) => e.kind)
    ).toEqual([ERR.nameTaken]);
    expect(fixture.componentInstance.canSave()).toBe(false);
  });
});
