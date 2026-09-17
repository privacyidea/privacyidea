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
import { By } from "@angular/platform-browser";
import { RefocusAfterReloadDirective } from "./refocus-after-reload.directive";

@Component({
  standalone: true,
  imports: [RefocusAfterReloadDirective],
  template: `<input [appRefocusAfterReload]="loading()" /><input id="other" />`
})
class HostComponent {
  readonly loading = signal(false);
}

describe("RefocusAfterReloadDirective", () => {
  let fixture: ComponentFixture<HostComponent>;
  let input: HTMLInputElement;
  let other: HTMLInputElement;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [HostComponent] });
    fixture = TestBed.createComponent(HostComponent);
    input = fixture.debugElement.query(By.css("input:not(#other)")).nativeElement;
    other = fixture.debugElement.query(By.css("#other")).nativeElement;
    document.body.appendChild(fixture.nativeElement);
    fixture.detectChanges();
  });

  afterEach(() => fixture.nativeElement.remove());

  it("refocuses the input once loading finishes, if it had focus when loading started", async () => {
    input.focus();
    fixture.componentInstance.loading.set(true);
    fixture.detectChanges();

    other.focus();
    fixture.componentInstance.loading.set(false);
    fixture.detectChanges();
    await Promise.resolve();

    expect(document.activeElement).toBe(input);
  });

  it("does not steal focus if the input was not focused when loading started", async () => {
    other.focus();
    fixture.componentInstance.loading.set(true);
    fixture.detectChanges();
    fixture.componentInstance.loading.set(false);
    fixture.detectChanges();
    await Promise.resolve();

    expect(document.activeElement).toBe(other);
  });
});
