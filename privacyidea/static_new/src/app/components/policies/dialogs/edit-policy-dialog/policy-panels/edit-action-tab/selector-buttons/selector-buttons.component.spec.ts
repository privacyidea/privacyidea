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
import { SelectorButtonsComponent } from "./selector-buttons.component";
import { By } from "@angular/platform-browser";
import { provideNoopAnimations } from "@angular/platform-browser/animations";

describe("SelectorButtonsComponent", () => {
  let component: SelectorButtonsComponent<string>;
  let fixture: ComponentFixture<SelectorButtonsComponent<string>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SelectorButtonsComponent],
      providers: [provideNoopAnimations()]
    }).compileComponents();

    fixture = TestBed.createComponent<SelectorButtonsComponent<string>>(SelectorButtonsComponent as any);
    component = fixture.componentInstance;

    fixture.componentRef.setInput("values", ["A", "B", "C"]);
    fixture.componentRef.setInput("initialValue", "A");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should have selected-button class on the initial value", () => {
    const selectedBtn = fixture.debugElement.query(By.css(".selected-button"));
    expect(selectedBtn.nativeElement.textContent.trim()).toBe("A");
  });

  it("should not lose selection class when becoming disabled", () => {
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();

    const selectedBtn = fixture.debugElement.query(By.css(".selected-button"));
    expect(selectedBtn).toBeTruthy();
    expect(selectedBtn.nativeElement.disabled).toBe(true);
  });

  it("should properly apply 'last-button' class to the correct element", () => {
    const buttons = fixture.debugElement.queryAll(By.css(".button-item"));
    expect(buttons[2].nativeElement.classList).toContain("last-button");
  });
});
