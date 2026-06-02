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
import { TokenEnrollmentPayload } from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";
import { MockContainerTemplateService } from "../../../../../testing/mock-services/mock-container-template-service";
import { ContainerTemplateEditComponent } from "./container-template-edit.component";

describe("ContainerTemplateEditComponent", () => {
  let component: ContainerTemplateEditComponent;
  let fixture: ComponentFixture<ContainerTemplateEditComponent>;
  let serviceMock: MockContainerTemplateService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateEditComponent],
      providers: [{ provide: ContainerTemplateService, useClass: MockContainerTemplateService }]
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

  it("nameConflict is false when name unchanged", () => {
    serviceMock.templates.set([
      { name: "Existing", container_type: "generic", default: false, template_options: { tokens: [] } }
    ]);
    expect(component.nameConflict()).toBe(false);
  });

  it("nameConflict is true when name matches an existing template", () => {
    serviceMock.templates.set([
      { name: "Existing", container_type: "generic", default: false, template_options: { tokens: [] } }
    ]);
    component.editTemplate({ name: "Existing" });
    expect(component.nameConflict()).toBe(true);
  });

  it("nameConflict is false when renamed to a unique name", () => {
    serviceMock.templates.set([
      { name: "Other", container_type: "generic", default: false, template_options: { tokens: [] } }
    ]);
    component.editTemplate({ name: "UniqueNewName" });
    expect(component.nameConflict()).toBe(false);
  });

  it("canSaveTemplate delegates to service.canSaveTemplate and respects nameConflict", () => {
    serviceMock.canSaveTemplate.mockReturnValue(true);
    expect(component.canSaveTemplate()).toBe(true);
    expect(serviceMock.canSaveTemplate).toHaveBeenCalledWith(component.template());

    serviceMock.templates.set([
      { name: "Conflict", container_type: "generic", default: false, template_options: { tokens: [] } }
    ]);
    component.editTemplate({ name: "Conflict" });
    expect(component.canSaveTemplate()).toBe(false);
  });

  it("canSaveTemplate is false when service returns false regardless of nameConflict", () => {
    serviceMock.canSaveTemplate.mockReturnValue(false);
    expect(component.canSaveTemplate()).toBe(false);
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

  it("nameErrorMatcher.isErrorState returns true on conflict", () => {
    serviceMock.templates.set([
      { name: "Taken", container_type: "generic", default: false, template_options: { tokens: [] } }
    ]);
    component.editTemplate({ name: "Taken" });
    expect(component.nameErrorMatcher.isErrorState()).toBe(true);
  });

  it("nameErrorMatcher.isErrorState returns false when no conflict", () => {
    component.editTemplate({ name: "Unique" });
    expect(component.nameErrorMatcher.isErrorState()).toBe(false);
  });
});
