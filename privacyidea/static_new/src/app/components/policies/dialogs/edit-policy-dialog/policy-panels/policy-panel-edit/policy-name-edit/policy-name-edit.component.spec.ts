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
import { PolicyNameEditComponent } from "./policy-name-edit.component";
import { FormsModule } from "@angular/forms";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("PolicyNameEditComponent", () => {
  let component: PolicyNameEditComponent;
  let fixture: ComponentFixture<PolicyNameEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyNameEditComponent, FormsModule, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyNameEditComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policyName", "Test Policy");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should update the model when policyName is changed", () => {
    const spy = jest.spyOn(component.policyName, "set");
    component.policyName.set("New Name");
    expect(spy).toHaveBeenCalledWith("New Name");
  });
});
