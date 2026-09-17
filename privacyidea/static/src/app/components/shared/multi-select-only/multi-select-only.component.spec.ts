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
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { MultiSelectOnlyComponent } from "./multi-select-only.component";

describe("MultiSelectOnlyComponent", () => {
  let component: MultiSelectOnlyComponent<string | number>;
  let fixture: ComponentFixture<MultiSelectOnlyComponent<string | number>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MultiSelectOnlyComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(MultiSelectOnlyComponent<string | number>);
    component = fixture.componentInstance;

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
      expect(component.triggerValue()).toBe("");
    });
  });

  describe("Single Selection (Toggle)", () => {
    it("should add item to selection if not present", () => {
      fixture.componentRef.setInput("items", ["A", "B"]);
      fixture.componentRef.setInput("selectedItems", ["A"]);
      fixture.detectChanges();
      const emitSpy = jest.spyOn(component.selectionChange, "emit");
      component.toggle("B");

      expect(emitSpy).toHaveBeenCalledWith(["A", "B"]);
    });

    it("should remove item from selection if already present", () => {
      fixture.componentRef.setInput("items", ["A", "B"]);
      fixture.componentRef.setInput("selectedItems", ["A", "B"]);
      fixture.detectChanges();
      const emitSpy = jest.spyOn(component.selectionChange, "emit");
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
      const mockEvent = { stopPropagation: jest.fn() } as unknown as MouseEvent;

      component.selectOnly(mockEvent, "B");

      expect(mockEvent.stopPropagation).toHaveBeenCalled();
      expect(emitSpy).toHaveBeenCalledWith(["B"]);
    });
  });

  describe("Toggle All", () => {
    it("should select all items if not all are currently selected", () => {
      fixture.componentRef.setInput("items", ["A", "B", "C"]);
      fixture.componentRef.setInput("selectedItems", ["A"]);
      fixture.detectChanges();

      const emitSpy = jest.spyOn(component.selectionChange, "emit");

      component.toggleAll();
      expect(emitSpy).toHaveBeenCalledWith(["A", "B", "C"]);
    });

    it("should deselect all items if all are currently selected", () => {
      fixture.componentRef.setInput("items", ["A", "B"]);
      fixture.componentRef.setInput("selectedItems", ["A", "B"]);
      fixture.detectChanges();

      const emitSpy = jest.spyOn(component.selectionChange, "emit");

      component.toggleAll();

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

  describe("Panel Keyboard Navigation", () => {
    let select: MatSelect;
    let emitSpy: jest.SpyInstance;
    let frames: FrameRequestCallback[];

    const press = (key: string): KeyboardEvent => {
      const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
      fixture.nativeElement.dispatchEvent(event);
      frames.splice(0).forEach((callback) => callback(0));
      fixture.detectChanges();
      return event;
    };

    const highlight = (index: number) => {
      select.options.forEach((option, i) => (i === index ? option.setActiveStyles() : option.setInactiveStyles()));
    };

    beforeEach(() => {
      frames = [];
      jest.spyOn(window, "requestAnimationFrame").mockImplementation((callback: FrameRequestCallback) => {
        frames.push(callback);
        return frames.length;
      });
      fixture.componentRef.setInput("items", ["A", "B", "C"]);
      fixture.componentRef.setInput("selectedItems", ["A"]);
      fixture.detectChanges();
      select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance;
      emitSpy = jest.spyOn(component.selectionChange, "emit");
    });

    afterEach(() => {
      if (select.panelOpen) {
        select.close();
      }
      jest.restoreAllMocks();
    });

    describe("with closed panel", () => {
      it("should ignore keys", () => {
        const event = press("Tab");

        expect(event.defaultPrevented).toBe(false);
        expect(component.keyFocus()).toBe("row");
      });
    });

    describe("with open panel", () => {
      beforeEach(() => {
        select.open();
        fixture.detectChanges();
      });

      it("should not take over Tab when no row is highlighted", () => {
        highlight(-1);

        const event = press("Tab");

        expect(event.defaultPrevented).toBe(false);
        expect(component.keyFocus()).toBe("row");
      });

      it("should move the marker between row and Only button on Tab", () => {
        highlight(1);

        const event = press("Tab");
        expect(event.defaultPrevented).toBe(true);
        expect(component.keyFocus()).toBe("only");

        press("Tab");
        expect(component.keyFocus()).toBe("row");
      });

      it("should select only the highlighted item on Enter while on the Only button", () => {
        highlight(1);
        press("Tab");

        const event = press("Enter");

        expect(event.defaultPrevented).toBe(true);
        expect(emitSpy).toHaveBeenCalledWith(["B"]);
        expect(component.keyFocus()).toBe("row");
      });

      it("should select only the highlighted item on Space while on the Only button", () => {
        highlight(2);
        press("Tab");

        press(" ");

        expect(emitSpy).toHaveBeenCalledWith(["C"]);
      });

      it("should do nothing on Enter on the Only button once the highlight is gone", () => {
        highlight(1);
        press("Tab");
        highlight(-1);

        const event = press("Enter");

        expect(event.defaultPrevented).toBe(false);
        expect(emitSpy).not.toHaveBeenCalled();
        expect(component.keyFocus()).toBe("only");
      });

      it("should hand the marker back to the row on any other key", () => {
        highlight(1);
        press("Tab");

        const event = press("ArrowDown");

        expect(event.defaultPrevented).toBe(false);
        expect(component.keyFocus()).toBe("row");
      });

      it("should leave Enter to MatSelect while on the row", () => {
        highlight(1);

        const event = press("Enter");

        expect(event.defaultPrevented).toBe(false);
        expect(emitSpy).not.toHaveBeenCalled();
      });

      it("should not enter the header on ArrowUp from a row other than the first", () => {
        highlight(1);

        const event = press("ArrowUp");

        expect(event.defaultPrevented).toBe(false);
        expect(component.keyFocus()).toBe("row");
      });

      it("should scroll the panel to the top when the first row is highlighted", () => {
        highlight(0);
        select.panel.nativeElement.scrollTop = 40;

        press("ArrowDown");

        expect(select.panel.nativeElement.scrollTop).toBe(0);
      });

      describe("header", () => {
        beforeEach(() => {
          highlight(0);
          press("ArrowUp");
        });

        it("should move the marker to the header on ArrowUp from the first row", () => {
          expect(component.keyFocus()).toBe("selectAll");
          expect(select.options.first.active).toBe(false);
        });

        it("should toggle all items on Enter", () => {
          const event = press("Enter");

          expect(event.defaultPrevented).toBe(true);
          expect(emitSpy).toHaveBeenCalledWith(["A", "B", "C"]);
          expect(component.keyFocus()).toBe("selectAll");
        });

        it("should toggle all items on Space", () => {
          press(" ");

          expect(emitSpy).toHaveBeenCalledWith(["A", "B", "C"]);
        });

        it("should stay on the header on ArrowUp", () => {
          const event = press("ArrowUp");

          expect(event.defaultPrevented).toBe(true);
          expect(component.keyFocus()).toBe("selectAll");
        });

        it("should return to the first row on ArrowDown", () => {
          const event = press("ArrowDown");

          expect(event.defaultPrevented).toBe(true);
          expect(component.keyFocus()).toBe("row");
          expect(select.options.first.active).toBe(true);
        });

        it("should return to the first row on any other key without swallowing it", () => {
          const event = press("Escape");

          expect(event.defaultPrevented).toBe(false);
          expect(component.keyFocus()).toBe("row");
          expect(select.options.first.active).toBe(true);
        });

        it("should reset the marker when the panel closes", async () => {
          select.close();
          await fixture.whenStable();

          expect(component.keyFocus()).toBe("row");
        });
      });
    });

    it("should stop listening once destroyed", () => {
      const host: HTMLElement = fixture.nativeElement;
      const removeSpy = jest.spyOn(host, "removeEventListener");

      fixture.destroy();

      expect(removeSpy).toHaveBeenCalledWith("keydown", expect.any(Function), true);
    });
  });
});
