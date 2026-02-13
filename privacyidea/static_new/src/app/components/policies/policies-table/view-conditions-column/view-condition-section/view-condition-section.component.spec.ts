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
import { ViewConditionSectionComponent } from "./view-condition-section.component";
import { By } from "@angular/platform-browser";

describe("ViewConditionSectionComponent", () => {
  let component: ViewConditionSectionComponent;
  let fixture: ComponentFixture<ViewConditionSectionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ViewConditionSectionComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ViewConditionSectionComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("label", "Initial Label");
    fixture.componentRef.setInput("values", []);
    fixture.detectChanges();
  });

  it("should be created", () => {
    expect(component).toBeTruthy();
  });

  describe("Label Rendering", () => {
    it("should render the label with a colon", () => {
      fixture.componentRef.setInput("label", "Realms");
      fixture.detectChanges();

      const labelEl = fixture.debugElement.query(By.css(".conditions-label")).nativeElement;
      expect(labelEl.textContent).toContain("Realms:");
    });
  });

  describe("Values (@for)", () => {
    it("should render a div for each value provided", () => {
      const testValues = ["val1", "val2", "val3"];
      fixture.componentRef.setInput("values", testValues);
      fixture.detectChanges();

      const chips = fixture.debugElement.queryAll(By.css(".conditions-chips-container div:not(.marker-chip)"));

      expect(chips.length).toBe(3);
      expect(chips[0].nativeElement.textContent.trim()).toBe("val1");
      expect(chips[2].nativeElement.textContent.trim()).toBe("val3");
    });

    it("should handle empty values array", () => {
      fixture.componentRef.setInput("values", []);
      fixture.detectChanges();

      const chips = fixture.debugElement.queryAll(By.css(".conditions-chips-container div:not(.marker-chip)"));
      expect(chips.length).toBe(0);
    });
  });

  describe("Marker (@if)", () => {
    it("should not show the marker-chip if marker input is empty", () => {
      fixture.componentRef.setInput("marker", undefined);
      fixture.detectChanges();

      const markerChip = fixture.debugElement.query(By.css(".marker-chip"));
      expect(markerChip).toBeNull();
    });

    it("should render the marker-chip when provided", () => {
      fixture.componentRef.setInput("marker", "NOT");
      fixture.detectChanges();

      const markerChip = fixture.debugElement.query(By.css(".marker-chip"));
      expect(markerChip).toBeTruthy();
      expect(markerChip.nativeElement.textContent.trim()).toBe("NOT");
    });
  });

  describe("Visual Structure", () => {
    it("should have the correct grid container class", () => {
      const container = fixture.debugElement.query(By.css(".conditions-grid-container"));
      expect(container).toBeTruthy();
    });
  });
});
