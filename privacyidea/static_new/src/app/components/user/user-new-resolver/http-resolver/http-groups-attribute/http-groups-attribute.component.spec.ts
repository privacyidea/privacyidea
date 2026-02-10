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
import { FormControl, FormGroup, ReactiveFormsModule } from "@angular/forms";
import { HttpGroupsAttributeComponent } from "./http-groups-attribute.component";

describe("HttpGroupsAttributeComponent", () => {
  let component: HttpGroupsAttributeComponent;
  let fixture: ComponentFixture<HttpGroupsAttributeComponent>;
  let userGroupsControl: FormGroup;

  beforeEach(async () => {
    userGroupsControl = new FormGroup({
      active: new FormControl(false),
      user_groups_attribute: new FormControl(""),
      method: new FormControl("get"),
      endpoint: new FormControl("")
    });

    await TestBed.configureTestingModule({
      imports: [HttpGroupsAttributeComponent, ReactiveFormsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(HttpGroupsAttributeComponent);
    component = fixture.componentInstance;
    component.userGroupsControl = userGroupsControl;
    component.resolverType = "default";
    fixture.detectChanges();
    await Promise.resolve();
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should enable controls when active is true", () => {
    // Check previous state due to inital values
    expect(userGroupsControl.get("user_groups_attribute")!.enabled).toBe(false);
    expect(userGroupsControl.get("method")!.enabled).toBe(false);
    expect(userGroupsControl.get("endpoint")!.enabled).toBe(false);

    // Change value to true
    userGroupsControl.get("active")!.setValue(true);
    fixture.detectChanges();
    expect(userGroupsControl.get("user_groups_attribute")!.enabled).toBe(true);
    expect(userGroupsControl.get("method")!.enabled).toBe(true);
    expect(userGroupsControl.get("endpoint")!.enabled).toBe(true);
  });

  it("should disable controls when active is false", async () => {
    component.userGroupsControl.get("active")!.setValue(false, { emitEvent: true });
    fixture.detectChanges();
    expect(component.userGroupsControl.get("user_groups_attribute")!.disabled).toBe(true);
    expect(component.userGroupsControl.get("method")!.disabled).toBe(true);
    expect(component.userGroupsControl.get("endpoint")!.disabled).toBe(true);
  });

  it("should normalize method value to lowercase", () => {
    userGroupsControl.get("method")!.setValue("GET");
    fixture.detectChanges();
    expect(userGroupsControl.get("method")!.value).toBe("get");
    userGroupsControl.get("method")!.setValue("PoSt");
    fixture.detectChanges();
    expect(userGroupsControl.get("method")!.value).toBe("post");
  });
});
