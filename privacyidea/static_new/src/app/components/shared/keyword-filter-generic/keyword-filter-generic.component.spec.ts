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
import { KeywordFilterGenericComponent } from "./keyword-filter-generic.component";
import { FilterValueGeneric } from "../../../core/models/filter_value_generic/filter-value-generic";
import { FilterOption } from "src/app/core/models/filter_value_generic/filter-option";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("KeywordFilterGenericComponent", () => {
  let component: KeywordFilterGenericComponent<any>;
  let fixture: ComponentFixture<KeywordFilterGenericComponent<any>>;
  let mockInput: HTMLInputElement;

  /**
   * Helper to create valid FilterOptions that satisfy the TypeScript interface.
   */
  const createOption = (key: string, label: string) =>
    new FilterOption<any>({
      key,
      label,
      matches: () => true // Default mock logic for UI-focused tests
    });

  const mockOptions: FilterOption<any>[] = [createOption("name", "Name"), createOption("active", "Active")];

  const advancedOptions: FilterOption<any>[] = [createOption("priority", "Priority")];

  const mockFilterModel = new FilterValueGeneric<any>({
    availableFilters: [...mockOptions, ...advancedOptions]
  });

  beforeEach(async () => {
    mockInput = document.createElement("input");

    await TestBed.configureTestingModule({
      imports: [KeywordFilterGenericComponent, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(KeywordFilterGenericComponent);
    component = fixture.componentInstance;

    /**
     * Component Input Setup using Angular Signals API
     */
    fixture.componentRef.setInput("filterOptions", mockOptions);
    fixture.componentRef.setInput("advancedKeywordFilters", advancedOptions);
    fixture.componentRef.setInput("filter", mockFilterModel);
    fixture.componentRef.setInput("filterHTMLInputElement", mockInput);

    fixture.detectChanges();
  });

  describe("UI Integrity", () => {
    it("should render correct number of primary buttons", () => {
      const buttons = fixture.nativeElement.querySelectorAll(".keyword-button");
      expect(buttons.length).toBe(2);
    });

    it("should toggle advanced section visibility via signal update", () => {
      const moreBtn = fixture.nativeElement.querySelector(".more-keyword-button");
      moreBtn.click();
      fixture.detectChanges();

      expect(component.showAdvancedFilter()).toBe(true);
      const buttons = fixture.nativeElement.querySelectorAll(".keyword-button");
      expect(buttons.length).toBe(3);
    });
  });

  describe("Model Interaction", () => {
    it("should emit new filter state on keyword click", () => {
      const outputSpy = jest.spyOn(component.filterChange, "emit");
      const buttons = fixture.nativeElement.querySelectorAll(".keyword-button");

      buttons[0].click();
      fixture.detectChanges();

      expect(outputSpy).toHaveBeenCalled();
      const emittedValue = outputSpy.mock.calls[0][0] as FilterValueGeneric<any>;
      expect(emittedValue.hasKey("name")).toBe(true);
    });

    it("should refocus the HTML input element after interaction", () => {
      const focusSpy = jest.spyOn(mockInput, "focus");
      const buttons = fixture.nativeElement.querySelectorAll(".keyword-button");

      buttons[0].click();

      expect(focusSpy).toHaveBeenCalled();
    });
  });

  describe("Visual Feedback", () => {
    it("should dynamically return icon names based on current model state", () => {
      const icon = component.getFilterIconName(mockOptions[0]);
      expect(icon).toBe("add_circle");

      // Update model state to include the key
      const updatedModel = mockFilterModel.addKey("name");
      fixture.componentRef.setInput("filter", updatedModel);
      fixture.detectChanges();

      expect(component.getFilterIconName(mockOptions[0])).toBe("remove_circle");
    });
  });
});
