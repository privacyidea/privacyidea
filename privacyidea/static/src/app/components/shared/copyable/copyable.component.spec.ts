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
import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FilterValueButtonComponent } from "@components/shared/filter-value-button/filter-value-button.component";
import { CopyableComponent } from "./copyable.component";

@Component({
  standalone: true,
  imports: [CopyableComponent, FilterValueButtonComponent],
  template: `
    <app-copyable [copyText]="value()">
      <span class="value">{{ value() }}</span>
      @if (showFilter()) {
        <app-filter-value-button [value]="value()" />
      }
    </app-copyable>
  `
})
class HostComponent {
  readonly value = signal("alice");
  readonly showFilter = signal(true);
}

describe("CopyableComponent", () => {
  let fixture: ComponentFixture<HostComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HostComponent] }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
  });

  function actions(): HTMLElement {
    return fixture.nativeElement.querySelector(".copyable-actions");
  }

  it("groups a filter button projected through a control flow block with the copy button", () => {
    const children = Array.from(actions().children).map((child) => child.tagName.toLowerCase());

    expect(children).toEqual(["app-filter-value-button", "app-copy-button"]);
  });

  it("keeps the value outside the action group", () => {
    expect(actions().querySelector(".value")).toBeNull();
    expect(fixture.nativeElement.querySelector(".value").textContent).toBe("alice");
  });

  it("holds only the copy button when there is no filter button", () => {
    fixture.componentInstance.showFilter.set(false);
    fixture.detectChanges();

    const children = Array.from(actions().children).map((child) => child.tagName.toLowerCase());
    expect(children).toEqual(["app-copy-button"]);
  });

  it("renders no copy button without text to copy", () => {
    fixture.componentInstance.value.set("");
    fixture.detectChanges();

    expect(actions().querySelector("app-copy-button")).toBeNull();
  });
});
