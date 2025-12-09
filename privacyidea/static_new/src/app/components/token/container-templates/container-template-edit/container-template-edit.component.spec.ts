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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ContainerTemplateEditComponent } from "./container-template-edit.component";
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ContainerTemplate } from "../../../../services/container/container.service";
import { MatExpansionPanel } from "@angular/material/expansion";
import { deepCopy } from "../../../../utils/deep-copy.utils";
import { MockContainerTemplateService } from "../../../../../testing/mock-services/mock-container-template-service";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("ContainerTemplateEditComponent", () => {
  let component: ContainerTemplateEditComponent;
  let fixture: ComponentFixture<ContainerTemplateEditComponent>;
  let containerTemplateServiceMock: MockContainerTemplateService;

  const mockTemplate: ContainerTemplate = {
    name: "Test Template",
    container_type: "generic",
    default: false,
    template_options: {
      tokens: [
        {
          type: "hotp",
          otpLength: 6,
          hashAlgorithm: "sha1",
          generateOnServer: true,
          timeStep: 30,
          user: true,
          otpKey: ""
        }
      ],
      options: undefined
    }
  };

  beforeEach(async () => {
    containerTemplateServiceMock = {
      canSaveTemplate: jest.fn(),
      postTemplateEdits: jest.fn(),
      deleteTemplate: jest.fn()
    } as any;

    await TestBed.configureTestingModule({
      imports: [ContainerTemplateEditComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateEditComponent);
    component = fixture.componentInstance;
    containerTemplateServiceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    fixture.componentRef.setInput("templateOriginal", mockTemplate);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("Initial State", () => {
    it("should be in view mode initially", () => {
      expect(component.isEditMode()).toBe(false);
    });

    it("should show the original template initially", () => {
      expect(component.currentTemplate()).toEqual(mockTemplate);
    });

    it("should indicate that the template is not edited initially", () => {
      expect(component.isTemplateEdited()).toBe(false);
    });
  });

  describe("Edit Mode", () => {
    it("should switch to edit mode and use the copied template", () => {
      component.isEditMode.set(true);
      fixture.detectChanges();

      expect(component.currentTemplate()).not.toBe(mockTemplate); // Should be a deep copy
      expect(component.currentTemplate()).toEqual(mockTemplate);
    });

    it("should not show as edited right after entering edit mode", () => {
      component.isEditMode.set(true);
      fixture.detectChanges();
      expect(component.isTemplateEdited()).toBe(false);
    });

    it("should detect changes when templateEdited is modified", () => {
      component.isEditMode.set(true);
      fixture.detectChanges();

      component.onNameChange("New Name");
      fixture.detectChanges();

      expect(component.isTemplateEdited()).toBe(true);
    });
  });

  describe("User Actions", () => {
    beforeEach(() => {
      component.isEditMode.set(true);
      fixture.detectChanges();
    });

    describe("saveTemplate", () => {
      it("should call the service to save the template if it can be saved", () => {
        containerTemplateServiceMock.canSaveTemplate.mockReturnValue(true);
        let test = component.templateEdited();
        const templateAfterEdit = { ...mockTemplate, name: "New Name" };
        component.isEditMode.set(true);
        component.onNameChange("New Name");
        component.saveTemplate();
        expect(containerTemplateServiceMock.postTemplateEdits).toHaveBeenCalledWith(templateAfterEdit);
        expect(component.isEditMode()).toBe(false);
      });

      it("should not call the service if the template cannot be saved", () => {
        containerTemplateServiceMock.canSaveTemplate.mockReturnValue(false);
        component.saveTemplate();
        expect(containerTemplateServiceMock.postTemplateEdits).not.toHaveBeenCalled();
        expect(component.isEditMode()).toBe(true); // Should remain in edit mode
      });
    });

    describe("deleteTemplate", () => {
      it("should call the service to delete if user confirms", () => {
        jest.spyOn(window, "confirm").mockReturnValue(true);

        component.deleteTemplate(mockTemplate.name);

        expect(containerTemplateServiceMock.deleteTemplate).toHaveBeenCalledWith(mockTemplate.name);
      });

      it("should not call the service to delete if user cancels", () => {
        jest.spyOn(window, "confirm").mockReturnValue(false);

        component.deleteTemplate(mockTemplate.name);

        expect(containerTemplateServiceMock.deleteTemplate).not.toHaveBeenCalled();
      });
    });

    describe("cancelEditMode", () => {
      it("should exit edit mode if there are no changes", () => {
        component.cancelEditMode();
        expect(component.isEditMode()).toBe(false);
      });

      it("should exit edit mode if user confirms discarding changes", () => {
        component.onNameChange("A change");
        jest.spyOn(window, "confirm").mockReturnValue(true);

        component.cancelEditMode();

        expect(component.isEditMode()).toBe(false);
      });

      it("should remain in edit mode if user cancels discarding changes", () => {
        component.onNameChange("A change");
        jest.spyOn(window, "confirm").mockReturnValue(false);

        component.cancelEditMode();

        expect(component.isEditMode()).toBe(true);
      });
    });

    describe("handleCollapse", () => {
      it("should exit edit mode and collapse the panel if there are no changes", () => {
        const panel = { open: jest.fn() } as unknown as MatExpansionPanel;
        component.handleCollapse(panel);
        expect(component.isEditMode()).toBe(false);
        expect(panel.open).not.toHaveBeenCalled();
      });

      it("should not exit edit mode and keep panel open if user cancels discard", () => {
        component.onNameChange("A change");
        jest.spyOn(window, "confirm").mockReturnValue(false);
        const panel = { open: jest.fn() } as unknown as MatExpansionPanel;

        component.handleCollapse(panel);

        expect(component.isEditMode()).toBe(true);
        expect(panel.open).toHaveBeenCalled();
      });
    });
  });

  describe("Template Editing Methods", () => {
    beforeEach(() => {
      component.isEditMode.set(true);
      fixture.detectChanges();
    });

    it("onNameChange should update the template name", () => {
      component.onNameChange("New Template Name");
      expect(component.templateEdited().name).toBe("New Template Name");
    });

    it("onTypeChange should update the container type", () => {
      component.onTypeChange("generic");
      expect(component.templateEdited().container_type).toBe("generic");
    });

    it("onDefaultToggle should toggle the default flag", () => {
      const initialDefault = component.currentTemplate().default;
      component.onDefaultToggle();
      expect(component.templateEdited().default).toBe(!initialDefault);
    });

    it("onAddToken should add a new token to the list", () => {
      const initialTokenCount = component.templateEdited().template_options.tokens.length;
      component.onAddToken("yubikey");
      const newTokens = component.templateEdited().template_options.tokens;
      expect(newTokens.length).toBe(initialTokenCount + 1);
      expect(newTokens[newTokens.length - 1].type).toBe("yubikey");
    });

    it("onEditToken should modify the correct token at a given index", () => {
      const patch = { otplen: 8 };
      component.onEditToken(patch, 0);
      expect(component.templateEdited().template_options.tokens[0].otplen).toBe(8);
    });

    it("onDeleteToken should remove a token at a given index", () => {
      const initialTokenCount = component.templateEdited().template_options.tokens.length;
      component.onDeleteToken(0);
      expect(component.templateEdited().template_options.tokens.length).toBe(initialTokenCount - 1);
    });

    it("should not allow edits when not in edit mode", () => {
      component.isEditMode.set(false);
      fixture.detectChanges();

      const originalEdited = deepCopy(component.templateEdited());

      component.onNameChange("Should not work");
      component.onAddToken("should not work");
      component.onEditToken({ otplen: 10 }, 0);
      component.onDeleteToken(0);

      expect(component.templateEdited()).toEqual(originalEdited);
    });
  });
});
