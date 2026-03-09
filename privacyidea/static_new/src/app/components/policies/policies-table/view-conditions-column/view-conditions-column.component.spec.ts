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
import { ViewConditionsColumnComponent } from "./view-conditions-column.component";
import { MatIconModule } from "@angular/material/icon";
import { ViewConditionSectionComponent } from "./view-condition-section/view-condition-section.component";
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { PolicyDetail } from "src/app/services/policies/policies.service";

describe("ConditionsTabComponent", () => {
  let component: ViewConditionsColumnComponent;
  let fixture: ComponentFixture<ViewConditionsColumnComponent>;

  const mockPolicy: PolicyDetail = {
    check_all_resolvers: false,
    name: "test-policy",
    priority: 10,
    active: true,
    scope: "authentication",
    adminrealm: ["adminRealm1"],
    adminuser: ["adminUser1"],
    realm: ["userRealm1"],
    resolver: ["resolver1"],
    user: ["user1"],
    user_case_insensitive: true,
    pinode: ["node1"],
    time: "08:00-17:00",
    client: ["client1"],
    user_agents: ["userAgent1"],
    conditions: [["token", "testKey", "equals", "testValue", true, "raise_error"]],
    action: {},
    description: "Test Description"
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ViewConditionsColumnComponent, MatIconModule, ViewConditionSectionComponent],
      providers: [provideNoopAnimations()]
    }).compileComponents();

    fixture = TestBed.createComponent(ViewConditionsColumnComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policy", mockPolicy);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should correctly compute selectedAdmins", () => {
    expect(component.selectedAdmins()).toEqual(["adminUser1"]);
  });

  it("should correctly compute selectedAdminrealm", () => {
    expect(component.selectedAdminrealm()).toEqual(["adminRealm1"]);
  });

  it("should correctly compute selectedRealms", () => {
    expect(component.selectedRealms()).toEqual(["userRealm1"]);
  });

  it("should correctly compute selectedResolvers", () => {
    expect(component.selectedResolvers()).toEqual(["resolver1"]);
  });

  it("should correctly compute selectedUsers", () => {
    expect(component.selectedUsers()).toEqual(["user1"]);
  });

  it("should correctly compute userCaseInsensitive", () => {
    expect(component.userCaseInsensitive()).toBeTruthy();
  });

  it("should correctly compute selectedPinodes", () => {
    expect(component.selectedPinodes()).toEqual(["node1"]);
  });

  it("should correctly compute selectedValidTime", () => {
    expect(component.selectedValidTime()).toEqual("08:00-17:00");
  });

  it("should correctly compute selectedClient", () => {
    expect(component.selectedClient()).toEqual(["client1"]);
  });

  it("should correctly compute selectedUserAgents", () => {
    expect(component.selectedUserAgents()).toEqual(["userAgent1"]);
  });

  it("should correctly compute additionalConditions", () => {
    expect(component.additionalConditions()).toEqual([
      ["token", "testKey", "equals", "testValue", true, "raise_error"]
    ]);
  });

  it("should return correct section label", () => {
    expect(component.getSectionLabel("token")).toBe("Token");
  });

  it("should return correct comparator label", () => {
    expect(component.getComparatorLabel("equals")).toBe("Equals");
  });

  it("should return correct missing data label", () => {
    expect(component.getMissingDataLabel("raise_error")).toBe("Raise error");
  });

  it("should return key if section label not found", () => {
    expect(component.getSectionLabel("nonExistentKey" as any)).toBe("nonExistentKey");
  });

  it("should return key if comparator label not found", () => {
    expect(component.getComparatorLabel("nonExistentKey" as any)).toBe("nonExistentKey");
  });

  it("should return key if missing data label not found", () => {
    expect(component.getMissingDataLabel("nonExistentKey" as any)).toBe("nonExistentKey");
  });
});
