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
import { ChangeDetectionStrategy, Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { disabled, form, FormField, required } from "@angular/forms/signals";
import { MatButtonToggleGroup, MatButtonToggleModule } from "@angular/material/button-toggle";
import { MatRadioGroup, MatRadioModule } from "@angular/material/radio";

/**
 * Pins how `[formField]` behaves on `mat-radio-group` and `mat-button-toggle-group`.
 */
@Component({
  selector: "app-spike-radio-toggle",
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormField, MatRadioModule, MatButtonToggleModule],
  template: `
    <mat-radio-group
      id="radio"
      [formField]="f.radio">
      <mat-radio-button value="a">a</mat-radio-button>
      <mat-radio-button value="b">b</mat-radio-button>
    </mat-radio-group>
    <mat-button-toggle-group
      id="toggle"
      [formField]="f.toggle">
      <mat-button-toggle value="a">a</mat-button-toggle>
      <mat-button-toggle value="b">b</mat-button-toggle>
    </mat-button-toggle-group>
    <mat-button-toggle-group
      id="toggle-multi"
      multiple
      [formField]="f.toggleMulti">
      <mat-button-toggle value="a">a</mat-button-toggle>
      <mat-button-toggle value="b">b</mat-button-toggle>
    </mat-button-toggle-group>
  `
})
class SpikeRadioToggleComponent {
  readonly model = signal({ radio: "", toggle: "", toggleMulti: [] as string[], lock: false });
  readonly f = form(this.model, (p) => {
    required(p.radio);
    required(p.toggle);
    disabled(p.radio, () => this.model().lock);
    disabled(p.toggle, () => this.model().lock);
  });
}

describe("signal forms on mat-radio-group and mat-button-toggle-group", () => {
  let fixture: ComponentFixture<SpikeRadioToggleComponent>;
  let host: SpikeRadioToggleComponent;
  let el: HTMLElement;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const radios = () => Array.from(el.querySelectorAll("#radio input[type=radio]")) as HTMLInputElement[];
  const toggleGroup = (id: string) => fixture.debugElement.query(By.css(`#${id}`)).injector.get(MatButtonToggleGroup);
  const toggleButtons = (id: string) => Array.from(el.querySelectorAll(`#${id} button`)) as HTMLButtonElement[];

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [SpikeRadioToggleComponent] }).compileComponents();
    fixture = TestBed.createComponent(SpikeRadioToggleComponent);
    host = fixture.componentInstance;
    el = fixture.nativeElement;
    await flush();
  });

  describe("mat-radio-group", () => {
    it("writes a model change to the control", async () => {
      host.model.update((m) => ({ ...m, radio: "b" }));
      await flush();
      expect(radios()[1].checked).toBe(true);
      expect(radios()[0].checked).toBe(false);
      expect(fixture.debugElement.query(By.directive(MatRadioGroup)).injector.get(MatRadioGroup).value).toBe("b");
    });

    it("writes a click to the model and marks the field dirty", async () => {
      expect(host.f.radio().dirty()).toBe(false);
      radios()[1].click();
      await flush();
      expect(host.model().radio).toBe("b");
      expect(host.f.radio().dirty()).toBe(true);
    });

    it("marks the field touched on blur", async () => {
      radios()[0].dispatchEvent(new Event("blur"));
      await flush();
      expect(host.f.radio().touched()).toBe(true);
    });

    it("reports required for the empty value", () => {
      expect(
        host.f
          .radio()
          .errors()
          .map((e) => e.kind)
      ).toEqual(["required"]);
    });

    it("pushes disabled() to the buttons", async () => {
      host.model.update((m) => ({ ...m, lock: true }));
      await flush();
      expect(radios().every((radio) => radio.disabled)).toBe(true);
      expect(host.f.radio().errors()).toEqual([]);
    });
  });

  describe("mat-button-toggle-group", () => {
    it("writes a model change to the control", async () => {
      host.model.update((m) => ({ ...m, toggle: "b" }));
      await flush();
      expect(toggleGroup("toggle").value).toBe("b");
      expect(el.querySelectorAll("#toggle mat-button-toggle")[1].classList).toContain("mat-button-toggle-checked");
    });

    it("writes a click to the model and marks the field dirty", async () => {
      expect(host.f.toggle().dirty()).toBe(false);
      toggleButtons("toggle")[1].click();
      await flush();
      expect(host.model().toggle).toBe("b");
      expect(host.f.toggle().dirty()).toBe(true);
    });

    it("marks the field touched on a selection change, not on blur", async () => {
      toggleButtons("toggle")[0].dispatchEvent(new Event("blur"));
      await flush();
      expect(host.f.toggle().touched()).toBe(false);
      toggleButtons("toggle")[0].click();
      await flush();
      expect(host.f.toggle().touched()).toBe(true);
    });

    it("pushes disabled() to the group", async () => {
      host.model.update((m) => ({ ...m, lock: true }));
      await flush();
      expect(toggleGroup("toggle").disabled).toBe(true);
      expect(toggleButtons("toggle").every((button) => button.disabled)).toBe(true);
    });

    it("binds a multiple group to a string array", async () => {
      toggleButtons("toggle-multi")[0].click();
      toggleButtons("toggle-multi")[1].click();
      await flush();
      expect(host.model().toggleMulti).toEqual(["a", "b"]);
      host.model.update((m) => ({ ...m, toggleMulti: ["b"] }));
      await flush();
      expect(el.querySelectorAll("#toggle-multi mat-button-toggle")[0].classList).not.toContain(
        "mat-button-toggle-checked"
      );
      expect(el.querySelectorAll("#toggle-multi mat-button-toggle")[1].classList).toContain(
        "mat-button-toggle-checked"
      );
    });
  });
});
