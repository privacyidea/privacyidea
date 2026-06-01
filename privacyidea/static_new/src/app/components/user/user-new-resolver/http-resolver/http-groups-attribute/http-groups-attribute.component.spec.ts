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
import { HttpGroupsAttributeComponent, UserGroupsModel } from "./http-groups-attribute.component";

describe("HttpGroupsAttributeComponent", () => {
  let component: HttpGroupsAttributeComponent;
  let fixture: ComponentFixture<HttpGroupsAttributeComponent>;

  const initialModel: UserGroupsModel = {
    active: false,
    pi_user_groups_key: "groups",
    user_groups_attribute: "",
    method: "GET",
    endpoint: ""
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HttpGroupsAttributeComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(HttpGroupsAttributeComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("model", { ...initialModel });
    fixture.componentRef.setInput("resolverType", "default");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should reflect active state from model", () => {
    expect(component.model().active).toBe(false);

    component.model.update((m) => ({ ...m, active: true }));
    fixture.detectChanges();

    expect(component.model().active).toBe(true);
  });

  it("should update model when active changes", () => {
    component.model.update((m) => ({ ...m, active: true }));
    fixture.detectChanges();
    expect(component.model().active).toBe(true);

    component.model.update((m) => ({ ...m, active: false }));
    fixture.detectChanges();
    expect(component.model().active).toBe(false);
  });

  it("should show correct tooltip based on active state", () => {
    expect(component.slideToggleTooltipSignal()).toContain("Enable");

    component.model.update((m) => ({ ...m, active: true }));
    fixture.detectChanges();
    expect(component.slideToggleTooltipSignal()).toContain("Disable");
  });
});
