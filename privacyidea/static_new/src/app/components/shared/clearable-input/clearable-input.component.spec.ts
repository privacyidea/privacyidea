/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { ClearableInputComponent } from "./clearable-input.component";

describe("ClearableInputComponent", () => {
  let component: ClearableInputComponent;
  let fixture: ComponentFixture<ClearableInputComponent>;

  TestBed.configureTestingModule({
    imports: [ClearableInputComponent]
  }).compileComponents();

  beforeEach(() => {
    fixture = TestBed.createComponent(ClearableInputComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create the component", () => {
    expect(component).toBeTruthy();
  });

  it("should have showClearButton as true by default", () => {
    expect(component.showClearButton).toBe(true);
  });

  it("should emit onClick event when clearInput is called", () => {
    jest.spyOn(component.onClick, "emit");
    component.clearInput();
    expect(component.onClick.emit).toHaveBeenCalled();
  });

  it("should allow showClearButton to be set to false", () => {
    component.showClearButton = false;
    expect(component.showClearButton).toBe(false);
  });
});
