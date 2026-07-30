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

    // Out-of-range targets are not handled, so the key falls through to mat-select. mat-select
    // drops horizontal keys while the panel is open and clamps vertical ones at the list ends.
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

    it("keeps the active option when ArrowDown would move below the last row", () => {
      setActive(5);
      pressKey(fixture, "ArrowDown");
      expect(activeIndex()).toBe(5);
    });

    it("leaves ArrowUp to mat-select's single-step move when there is no row above", () => {
      setActive(1);
      pressKey(fixture, "ArrowUp");
      expect(activeIndex()).toBe(0);
    });

    it("leaves ArrowDown to mat-select's single-step move when the row below is incomplete", () => {
      fixture.componentInstance.options = ["a", "b", "c", "d", "e"];
      fixture.detectChanges();
      setActive(4);

      pressKey(fixture, "ArrowDown");

      // 4 is the only option in the last row; 4 + 2 is out of range, so mat-select clamps at 4.
      expect(activeIndex()).toBe(4);
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
