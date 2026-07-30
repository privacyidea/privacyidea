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
import { Component, ViewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { GridSelectNavDirective } from "./grid-select-nav.directive";

/** `keyCode` is a jsdom/legacy extension of `KeyboardEventInit`; MatSelect still reads it. */
type LegacyKeyboardEventInit = KeyboardEventInit & { keyCode?: number };

const KEY_CODES: Record<string, number> = {
  ArrowLeft: 37,
  ArrowUp: 38,
  ArrowRight: 39,
  ArrowDown: 40,
  Enter: 13
};

@Component({
  standalone: true,
  imports: [MatSelectModule, GridSelectNavDirective],
  template: `
    <mat-select
      appGridSelectNav
      [appGridSelectColumns]="columns">
      @for (option of options; track option) {
        <mat-option [value]="option">{{ option }}</mat-option>
      }
    </mat-select>
  `
})
class ConfiguredColumnsHostComponent {
  @ViewChild(MatSelect) select!: MatSelect;
  columns = 2;
  options = ["a", "b", "c", "d", "e", "f"];
}

@Component({
  standalone: true,
  imports: [MatSelectModule, GridSelectNavDirective],
  template: `
    <mat-select appGridSelectNav>
      @for (option of options; track option) {
        <mat-option [value]="option">{{ option }}</mat-option>
      }
    </mat-select>
  `
})
class AutoColumnsHostComponent {
  @ViewChild(MatSelect) select!: MatSelect;
  options = ["a", "b", "c", "d", "e", "f"];
}

describe("GridSelectNavDirective", () => {
  let fixture: ComponentFixture<ConfiguredColumnsHostComponent>;
  let select: MatSelect;

  function render<T extends { select: MatSelect }>(type: new () => T): ComponentFixture<T> {
    const created = TestBed.createComponent(type);
    created.detectChanges();
    return created;
  }

  /** Opens the panel so the options are rendered into the overlay and the key manager is live. */
  function openPanel(target: ComponentFixture<{ select: MatSelect }>): void {
    target.componentInstance.select.open();
    target.detectChanges();
  }

  function selectEl(target: ComponentFixture<unknown>): HTMLElement {
    return target.nativeElement.querySelector("mat-select") as HTMLElement;
  }

  function pressKey(
    target: ComponentFixture<unknown>,
    key: string,
    modifiers: Partial<LegacyKeyboardEventInit> = {}
  ): KeyboardEvent {
    const event = new KeyboardEvent("keydown", {
      key,
      keyCode: KEY_CODES[key],
      bubbles: true,
      cancelable: true,
      ...modifiers
    } as LegacyKeyboardEventInit);
    selectEl(target).dispatchEvent(event);
    target.detectChanges();
    return event;
  }

  function activeIndex(instance: MatSelect = select): number | null {
    return instance._keyManager.activeItemIndex;
  }

  function setActive(index: number, instance: MatSelect = select): void {
    instance._keyManager.updateActiveItem(index);
  }

  /**
   * jsdom reports `offsetTop: 0` for every element, so the auto-detection would see a single row.
   * Stub the option offsets to emulate a rendered `columns`-wide grid.
   */
  function layOutAsGrid(columns: number, instance: MatSelect = select): void {
    const panel = instance.panel.nativeElement as HTMLElement;
    Array.from(panel.querySelectorAll<HTMLElement>("mat-option")).forEach((el, index) =>
      Object.defineProperty(el, "offsetTop", { value: Math.floor(index / columns) * 40, configurable: true })
    );
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfiguredColumnsHostComponent, AutoColumnsHostComponent]
    }).compileComponents();
    fixture = render(ConfiguredColumnsHostComponent);
    select = fixture.componentInstance.select;
  });

  it("renders the options into the panel and starts with the first one active", () => {
    openPanel(fixture);
    expect(select.options.length).toBe(6);
    expect(activeIndex()).toBe(0);
  });

  describe("with a configured column count", () => {
    beforeEach(() => openPanel(fixture));

    it("moves down a whole row on ArrowDown instead of a single option", () => {
      setActive(0);
      pressKey(fixture, "ArrowDown");
      expect(activeIndex()).toBe(2);
    });

    it("moves up a whole row on ArrowUp", () => {
      setActive(5);
      pressKey(fixture, "ArrowUp");
      expect(activeIndex()).toBe(3);
    });

    it("moves a single option on ArrowRight", () => {
      setActive(0);
      pressKey(fixture, "ArrowRight");
      expect(activeIndex()).toBe(1);
    });

    it("moves a single option on ArrowLeft", () => {
      setActive(3);
      pressKey(fixture, "ArrowLeft");
      expect(activeIndex()).toBe(2);
    });

    it("wraps across rows when moving horizontally past a row edge", () => {
      setActive(1);
      pressKey(fixture, "ArrowRight");
      expect(activeIndex()).toBe(2);
    });

    // Horizontal targets outside the option list are swallowed, so mat-select never gets to apply
    // its own single-option step and moving off either end of the list does nothing.
    it("keeps the active option when ArrowLeft would move before the first option", () => {
      setActive(0);
      pressKey(fixture, "ArrowLeft");
      expect(activeIndex()).toBe(0);
    });

    it("keeps the active option when ArrowRight would move past the last option", () => {
      setActive(5);
      pressKey(fixture, "ArrowRight");
      expect(activeIndex()).toBe(5);
    });

    it("continues at the top of the next column on ArrowDown from the bottom of a column", () => {
      setActive(4);
      pressKey(fixture, "ArrowDown");
      expect(activeIndex()).toBe(1);
    });

    it("returns to the first column on ArrowDown from the bottom of the last column", () => {
      setActive(5);
      pressKey(fixture, "ArrowDown");
      expect(activeIndex()).toBe(0);
    });

    it("continues at the bottom of the previous column on ArrowUp from the top of a column", () => {
      setActive(1);
      pressKey(fixture, "ArrowUp");
      expect(activeIndex()).toBe(4);
    });

    it("returns to the last column on ArrowUp from the top of the first column", () => {
      setActive(0);
      pressKey(fixture, "ArrowUp");
      expect(activeIndex()).toBe(5);
    });

    it("cycles through every option when ArrowDown is held", () => {
      setActive(0);
      const visited = [0];
      for (let i = 0; i < 6; i++) {
        pressKey(fixture, "ArrowDown");
        visited.push(activeIndex());
      }

      expect(visited).toEqual([0, 2, 4, 1, 3, 5, 0]);
    });

    it("cycles backwards through every option when ArrowUp is held", () => {
      setActive(0);
      const visited = [0];
      for (let i = 0; i < 6; i++) {
        pressKey(fixture, "ArrowUp");
        visited.push(activeIndex());
      }

      expect(visited).toEqual([0, 5, 3, 1, 4, 2, 0]);
    });

    it("skips the empty cells of an incomplete last row while cycling", () => {
      fixture.componentInstance.options = ["a", "b", "c", "d", "e"];
      fixture.detectChanges();
      setActive(0);
      const visited = [0];
      for (let i = 0; i < 5; i++) {
        pressKey(fixture, "ArrowDown");
        visited.push(activeIndex());
      }

      // Index 5 does not exist, so the right column ends at 3 and the circle closes there.
      expect(visited).toEqual([0, 2, 4, 1, 3, 0]);
    });

    it("prevents the default on a horizontal edge move so mat-select cannot step a single option", () => {
      setActive(0);
      const laterListener = jest.fn();
      selectEl(fixture).addEventListener("keydown", laterListener);

      const event = pressKey(fixture, "ArrowLeft");

      expect(event.defaultPrevented).toBe(true);
      expect(laterListener).not.toHaveBeenCalled();
      expect(activeIndex()).toBe(0);
    });

    it("activates the first option when no option is active yet", () => {
      setActive(-1);
      pressKey(fixture, "ArrowRight");
      expect(activeIndex()).toBe(0);
    });

    it("prevents the default and keeps mat-select from navigating as well", () => {
      setActive(0);
      const laterListener = jest.fn();
      selectEl(fixture).addEventListener("keydown", laterListener);

      const event = pressKey(fixture, "ArrowDown");

      expect(event.defaultPrevented).toBe(true);
      expect(laterListener).not.toHaveBeenCalled();
      expect(activeIndex()).toBe(2);
    });
  });

  describe("keys it does not handle", () => {
    beforeEach(() => openPanel(fixture));

    it.each(["altKey", "ctrlKey", "metaKey", "shiftKey"] as const)(
      "ignores ArrowDown pressed with %s and leaves it to mat-select",
      (modifier) => {
        setActive(0);
        pressKey(fixture, "ArrowDown", { [modifier]: true });
        expect(activeIndex()).not.toBe(2);
      }
    );

    it("does not touch the active option on Enter", () => {
      setActive(2);
      pressKey(fixture, "Enter");
      expect(activeIndex()).toBe(2);
    });

    it("does nothing while the panel is closed", () => {
      select.close();
      fixture.detectChanges();
      setActive(0);

      pressKey(fixture, "ArrowDown");

      // mat-select's closed-panel handling steps to the next option; no row jump happens.
      expect(activeIndex()).toBe(1);
    });

    it("does nothing when the select has no options", () => {
      fixture.componentInstance.options = [];
      fixture.detectChanges();
      const setActiveItem = jest.spyOn(select._keyManager, "setActiveItem");

      pressKey(fixture, "ArrowDown");

      expect(select.options.length).toBe(0);
      expect(setActiveItem).not.toHaveBeenCalled();
    });
  });

  describe("without a configured column count", () => {
    let autoFixture: ComponentFixture<AutoColumnsHostComponent>;
    let autoSelect: MatSelect;

    beforeEach(() => {
      autoFixture = render(AutoColumnsHostComponent);
      autoSelect = autoFixture.componentInstance.select;
      openPanel(autoFixture);
    });

    it("derives the column count from the option positions in the rendered panel", () => {
      layOutAsGrid(3, autoSelect);
      setActive(0, autoSelect);

      pressKey(autoFixture, "ArrowDown");

      expect(activeIndex(autoSelect)).toBe(3);
    });

    it("falls back to a single column when every option sits on its own row", () => {
      layOutAsGrid(1, autoSelect);
      setActive(0, autoSelect);

      pressKey(autoFixture, "ArrowDown");

      expect(activeIndex(autoSelect)).toBe(1);
    });
  });

  it("treats a non-positive configured column count as unconfigured and measures the layout", () => {
    fixture.componentInstance.columns = 0;
    fixture.detectChanges();
    openPanel(fixture);
    layOutAsGrid(2);
    setActive(0);

    pressKey(fixture, "ArrowDown");

    expect(activeIndex()).toBe(2);
  });

  it("stops listening for keydown once destroyed", () => {
    openPanel(fixture);
    const removeEventListener = jest.spyOn(selectEl(fixture), "removeEventListener");

    fixture.destroy();

    expect(removeEventListener).toHaveBeenCalledWith("keydown", expect.any(Function), true);
  });
});
