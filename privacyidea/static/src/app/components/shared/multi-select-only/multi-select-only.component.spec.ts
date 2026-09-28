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
    let selectHost: HTMLElement;
    let emitSpy: jest.SpyInstance;
    let frames: Map<number, FrameRequestCallback>;
    let nextFrame: number;
    let fixtureDestroyed: boolean;

    const keyCodes: Record<string, number> = {
      Tab: 9,
      Enter: 13,
      Shift: 16,
      Escape: 27,
      " ": 32,
      End: 35,
      ArrowUp: 38,
      ArrowDown: 40
    };

    /**
     * Sends the key to the element MatSelect listens on, so its own key manager moves the
     * highlight exactly as it does in a browser. Material reads `keyCode`, which jsdom leaves at 0
     * for a constructed event.
     */
    const dispatch = (key: string, options: { shift?: boolean } = {}): KeyboardEvent => {
      const event = new KeyboardEvent("keydown", {
        key,
        bubbles: true,
        cancelable: true,
        shiftKey: options.shift ?? false
      });
      Object.defineProperty(event, "keyCode", { get: () => keyCodes[key] ?? 0 });
      selectHost.dispatchEvent(event);
      return event;
    };

    const press = (key: string, options: { shift?: boolean } = {}): KeyboardEvent => {
      const event = dispatch(key, options);
      const pending = [...frames.values()];
      frames.clear();
      pending.forEach((callback) => callback(0));
      fixture.detectChanges();
      return event;
    };

    const activeIndexes = () =>
      select.options.toArray().reduce<number[]>((found, option, index) => {
        return option.active ? [...found, index] : found;
      }, []);

    const clearHighlight = () => {
      select._keyManager.updateActiveItem(-1);
      select.options.forEach((option) => option.setInactiveStyles());
    };

    beforeEach(() => {
      frames = new Map();
      nextFrame = 0;
      fixtureDestroyed = false;
      jest.spyOn(window, "requestAnimationFrame").mockImplementation((callback: FrameRequestCallback) => {
        nextFrame += 1;
        frames.set(nextFrame, callback);
        return nextFrame;
      });
      jest.spyOn(window, "cancelAnimationFrame").mockImplementation((handle: number) => {
        frames.delete(handle);
      });
      fixture.componentRef.setInput("items", ["A", "B", "C"]);
      fixture.componentRef.setInput("selectedItems", ["A"]);
      fixture.detectChanges();
      select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance;
      selectHost = fixture.debugElement.query(By.directive(MatSelect)).nativeElement;
      emitSpy = jest.spyOn(component.selectionChange, "emit");
    });

    afterEach(() => {
      if (!fixtureDestroyed && select.panelOpen) {
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

      it("should highlight the selected row when the panel opens", () => {
        expect(activeIndexes()).toEqual([0]);
      });

      it("should not take over Tab when no row is highlighted", () => {
        clearHighlight();

        const event = press("Tab");

        expect(event.defaultPrevented).toBe(false);
        expect(component.keyFocus()).toBe("row");
      });

      it("should move the marker between row and Only button on Tab", () => {
        press("ArrowDown");
        expect(activeIndexes()).toEqual([1]);

        const event = press("Tab");
        expect(event.defaultPrevented).toBe(true);
        expect(component.keyFocus()).toBe("only");

        press("Tab", { shift: true });
        expect(component.keyFocus()).toBe("row");
      });

      it("should hand Tab off the Only button back to MatSelect", () => {
        press("ArrowDown");
        press("Tab");

        const event = press("Tab");

        expect(event.defaultPrevented).toBe(false);
        expect(component.keyFocus()).toBe("row");
        expect(select.panelOpen).toBe(false);
      });

      it("should step back to the row on shift+Tab from the Only button", () => {
        press("ArrowDown");
        press("Tab");

        const event = press("Tab", { shift: true });

        expect(event.defaultPrevented).toBe(true);
        expect(component.keyFocus()).toBe("row");
        expect(select.panelOpen).toBe(true);
      });

      it("should leave shift+Tab on the row to MatSelect", () => {
        press("ArrowDown");

        const event = press("Tab", { shift: true });

        expect(event.defaultPrevented).toBe(false);
        expect(select.panelOpen).toBe(false);
      });

      it("should select only the highlighted item on Enter while on the Only button", () => {
        press("ArrowDown");
        press("Tab");

        const event = press("Enter");

        expect(event.defaultPrevented).toBe(true);
        expect(emitSpy).toHaveBeenCalledWith(["B"]);
        expect(component.keyFocus()).toBe("row");
      });

      it("should select only the highlighted item on Space while on the Only button", () => {
        press("ArrowDown");
        press("ArrowDown");
        press("Tab");

        press(" ");

        expect(emitSpy).toHaveBeenCalledWith(["C"]);
      });

      it("should do nothing on Enter on the Only button once the highlight is gone", () => {
        press("ArrowDown");
        press("Tab");
        clearHighlight();

        press("Enter");

        expect(emitSpy).not.toHaveBeenCalled();
        expect(component.keyFocus()).toBe("only");
      });

      it("should keep the marker on the Only button when only a modifier is pressed", () => {
        press("ArrowDown");
        press("Tab");

        const event = press("Shift", { shift: true });

        expect(event.defaultPrevented).toBe(false);
        expect(component.keyFocus()).toBe("only");
      });

      it("should hand the marker back to the row on any other key", () => {
        press("ArrowDown");
        press("Tab");

        press("ArrowDown");

        expect(component.keyFocus()).toBe("row");
        expect(activeIndexes()).toEqual([2]);
      });

      it("should leave Enter on the row to MatSelect, which toggles it", () => {
        press("ArrowDown");

        press("Enter");

        expect(emitSpy).toHaveBeenCalledWith(["A", "B"]);
      });

      it("should keep the highlight when the parent writes the selection back", () => {
        press("ArrowDown");

        fixture.componentRef.setInput("selectedItems", ["B"]);
        fixture.detectChanges();

        expect(activeIndexes()).toEqual([1]);
      });

      it("should not enter the header on ArrowUp from a row other than the first", () => {
        press("ArrowDown");

        press("ArrowUp");

        expect(component.keyFocus()).toBe("row");
        expect(activeIndexes()).toEqual([0]);
      });

      it("should scroll the panel to the top when a key moves the highlight onto the first row", () => {
        press("ArrowDown");
        select.panel.nativeElement.scrollTop = 40;

        press("ArrowUp");

        expect(select.panel.nativeElement.scrollTop).toBe(0);
      });

      it("should leave a hand-scrolled panel alone when the key does not move the highlight", () => {
        select.panel.nativeElement.scrollTop = 40;

        press("ArrowUp");

        expect(select.panel.nativeElement.scrollTop).toBe(40);
      });

      it("should drop the pending frame when destroyed", () => {
        dispatch("ArrowDown");
        const handle: number = component["scrollFrame"];
        expect(frames.has(handle)).toBe(true);

        fixtureDestroyed = true;
        fixture.destroy();

        expect(frames.has(handle)).toBe(false);
      });

      describe("header", () => {
        beforeEach(() => {
          press("ArrowUp");
        });

        it("should move the marker to the header on ArrowUp from the first row", () => {
          expect(component.keyFocus()).toBe("selectAll");
          expect(activeIndexes()).toEqual([]);
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
          expect(activeIndexes()).toEqual([0]);
        });

        it("should return to the row on any other key without swallowing it", () => {
          press("End");

          expect(component.keyFocus()).toBe("row");
          expect(activeIndexes()).toEqual([2]);
        });

        it("should hand the highlight back to the row a click moved it to", () => {
          select.options.toArray()[2]._selectViaInteraction();
          fixture.detectChanges();

          expect(component.keyFocus()).toBe("row");
          expect(activeIndexes()).toEqual([2]);
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

      fixtureDestroyed = true;
      fixture.destroy();

      expect(removeSpy).toHaveBeenCalledWith("keydown", expect.any(Function), true);
    });
  });
});
