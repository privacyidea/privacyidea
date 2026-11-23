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
import { ComponentFixture } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { MatSelect } from "@angular/material/select";

/** Runs change detection and waits until the fixture is stable, then renders once more. */
export async function flushFixture(fixture: ComponentFixture<unknown>): Promise<void> {
  fixture.detectChanges();
  await fixture.whenStable();
  fixture.detectChanges();
}

/** The native input of the `mat-checkbox` matching `selector`. */
export function checkboxInput(fixture: ComponentFixture<unknown>, selector = "mat-checkbox"): HTMLInputElement {
  return fixture.nativeElement.querySelector(`${selector} input[type="checkbox"]`) as HTMLInputElement;
}

/** Clicks the native input of the `mat-checkbox` matching `selector` and renders. */
export async function clickCheckbox(fixture: ComponentFixture<unknown>, selector = "mat-checkbox"): Promise<void> {
  checkboxInput(fixture, selector).click();
  await flushFixture(fixture);
}

/** The `index`-th `mat-select` of the fixture. */
export function matSelectAt(fixture: ComponentFixture<unknown>, index = 0): MatSelect {
  return fixture.debugElement.queryAll(By.directive(MatSelect))[index].componentInstance as MatSelect;
}

/** Opens `select`, clicks the `optionIndex`-th option of its panel and renders. */
export async function pickOption(
  fixture: ComponentFixture<unknown>,
  select: MatSelect,
  optionIndex: number
): Promise<void> {
  select.open();
  await flushFixture(fixture);
  (select.panel.nativeElement.querySelectorAll("mat-option")[optionIndex] as HTMLElement).click();
  await flushFixture(fixture);
}

/** Removes the panels that opened selects and autocompletes leave in the overlay container. */
export function clearOverlays(): void {
  document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
}

/** Types `value` into `input` the way a user does, so the bound field becomes dirty. */
export async function typeInto(
  fixture: ComponentFixture<unknown>,
  input: HTMLInputElement | HTMLTextAreaElement,
  value: string
): Promise<void> {
  input.value = value;
  input.dispatchEvent(new Event("input"));
  await flushFixture(fixture);
}
