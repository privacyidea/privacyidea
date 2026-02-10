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
import { MultiSelectOnlyComponent } from "./multi-select-only.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("MultiSelectOnlyComponent", () => {
  let component: MultiSelectOnlyComponent;
  let fixture: ComponentFixture<MultiSelectOnlyComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MultiSelectOnlyComponent, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(MultiSelectOnlyComponent);
    component = fixture.componentInstance;

    // Initialisierung mit leeren Werten, um undefined Fehler zu vermeiden
    fixture.componentRef.setInput("items", []);
    fixture.componentRef.setInput("selectedItems", []);
    fixture.detectChanges();
  });

  describe("Computed Signals & State", () => {
    it("should remove duplicates from items", () => {
      fixture.componentRef.setInput("items", ["A", "B", "A", "C", "B"]);
      fixture.detectChanges();

      expect(component.uniqueItems()).toEqual(["A", "B", "C"]);
    });

    it("should return false for isAllSelected if lists differ", () => {
      fixture.componentRef.setInput("items", ["A", "B"]);
      fixture.componentRef.setInput("selectedItems", ["A"]);
      fixture.detectChanges();

      expect(component.isAllSelected()).toBe(false);
    });

    it("should return true for isAllSelected if all items are selected", () => {
      fixture.componentRef.setInput("items", ["A", "B"]);
      fixture.componentRef.setInput("selectedItems", ["A", "B"]);
      fixture.detectChanges();

      expect(component.isAllSelected()).toBe(true);
    });

    it("should handle empty selection for triggerValue", () => {
      fixture.componentRef.setInput("items", ["A", "B"]);
      fixture.componentRef.setInput("selectedItems", []);
      fixture.detectChanges();

      // Annahme: Wenn nichts ausgewählt ist, ist der Text leer oder Placeholder
      // (Hier prüfen wir auf leer, da kein Placeholder Input definiert war)
      expect(component.triggerValue()).toBe("");
    });
  });

  describe("Single Selection (Toggle)", () => {
    it("should add item to selection if not present", () => {
      fixture.componentRef.setInput("items", ["A", "B"]);
      fixture.componentRef.setInput("selectedItems", ["A"]);
      fixture.detectChanges();

      const emitSpy = jest.spyOn(component.selectionChange, "emit");

      // Wir simulieren das Togglen von 'B'
      component.toggle("B");

      expect(emitSpy).toHaveBeenCalledWith(["A", "B"]);
    });

    it("should remove item from selection if already present", () => {
      fixture.componentRef.setInput("items", ["A", "B"]);
      fixture.componentRef.setInput("selectedItems", ["A", "B"]);
      fixture.detectChanges();

      const emitSpy = jest.spyOn(component.selectionChange, "emit");

      // Wir simulieren das Togglen von 'B'
      component.toggle("B");

      expect(emitSpy).toHaveBeenCalledWith(["A"]);
    });
  });

  describe("Select Only (One Item)", () => {
    it("should select only the target item and stop event propagation", () => {
      fixture.componentRef.setInput("items", ["A", "B", "C"]);
      fixture.componentRef.setInput("selectedItems", ["A", "C"]);
      fixture.detectChanges();

      const emitSpy = jest.spyOn(component.selectionChange, "emit");

      // Mock für das Event erstellen, um stopPropagation zu prüfen
      const mockEvent = { stopPropagation: jest.fn() } as unknown as MouseEvent;

      component.selectOnly(mockEvent, "B");

      expect(mockEvent.stopPropagation).toHaveBeenCalled();
      expect(emitSpy).toHaveBeenCalledWith(["B"]);
    });
  });

  describe("Toggle All", () => {
    it("should select all items if not all are currently selected", () => {
      fixture.componentRef.setInput("items", ["A", "B", "C"]);
      fixture.componentRef.setInput("selectedItems", ["A"]); // Nur einer ausgewählt
      fixture.detectChanges();

      const emitSpy = jest.spyOn(component.selectionChange, "emit");

      component.toggleAll();

      // Erwartung: Alle unique Items werden emittet
      expect(emitSpy).toHaveBeenCalledWith(["A", "B", "C"]);
    });

    it("should deselect all items if all are currently selected", () => {
      fixture.componentRef.setInput("items", ["A", "B"]);
      fixture.componentRef.setInput("selectedItems", ["A", "B"]); // Alle ausgewählt
      fixture.detectChanges();

      const emitSpy = jest.spyOn(component.selectionChange, "emit");

      component.toggleAll();

      // Erwartung: Leeres Array wird emittet
      expect(emitSpy).toHaveBeenCalledWith([]);
    });

    it("should handle empty items list gracefully", () => {
      fixture.componentRef.setInput("items", []);
      fixture.componentRef.setInput("selectedItems", []);
      fixture.detectChanges();

      const emitSpy = jest.spyOn(component.selectionChange, "emit");

      component.toggleAll();

      expect(emitSpy).toHaveBeenCalledWith([]);
    });
  });
});
