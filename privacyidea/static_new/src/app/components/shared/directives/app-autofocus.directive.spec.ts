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
import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { AutofocusDirective } from "./app-autofocus.directive";

@Component({
  standalone: true,
  imports: [AutofocusDirective],
  template: `<input
    id="direct"
    appAutofocus />`
})
class DirectInputHostComponent {}

@Component({
  standalone: true,
  imports: [AutofocusDirective],
  template: `
    <div appAutofocus>
      <span>label</span>
      <input id="nested" />
    </div>
  `
})
class NestedInputHostComponent {}

@Component({
  standalone: true,
  imports: [AutofocusDirective],
  template: `<div appAutofocus><span>nothing to focus</span></div>`
})
class NoFocusableHostComponent {}

const flushMicrotasks = () => new Promise<void>((resolve) => queueMicrotask(resolve));

async function render<T>(type: new () => T): Promise<ComponentFixture<T>> {
  await TestBed.configureTestingModule({ imports: [type] }).compileComponents();
  const fixture = TestBed.createComponent(type);
  fixture.detectChanges();
  await flushMicrotasks();
  return fixture;
}

describe("AutofocusDirective", () => {
  it("focuses the host element itself when it is an input", async () => {
    const fixture = await render(DirectInputHostComponent);
    const input = fixture.nativeElement.querySelector("#direct") as HTMLInputElement;
    expect(document.activeElement).toBe(input);
  });

  it("focuses the first focusable descendant when the host is a container", async () => {
    const fixture = await render(NestedInputHostComponent);
    const input = fixture.nativeElement.querySelector("#nested") as HTMLInputElement;
    expect(document.activeElement).toBe(input);
  });

  it("does nothing when neither host nor descendants are focusable", async () => {
    const fixture = await render(NoFocusableHostComponent);
    expect(document.activeElement).not.toBe(fixture.nativeElement.querySelector("span"));
  });
});
