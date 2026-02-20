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
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockRealmService } from "../../../../../../../../testing/mock-services";
import { MockPolicyService } from "../../../../../../../../testing/mock-services/mock-policies-service";
import { MockResolverService } from "../../../../../../../../testing/mock-services/mock-resolver-service";
import { PolicyService } from "../../../../../../../services/policies/policies.service";
import { RealmService } from "../../../../../../../services/realm/realm.service";
import { ResolverService } from "../../../../../../../services/resolver/resolver.service";
import { EditUserConditionsComponent } from "./edit-user-conditions.component";
import { ReactiveFormsModule } from "@angular/forms";

describe("EditUserConditionsComponent", () => {
  let component: EditUserConditionsComponent;
  let fixture: ComponentFixture<EditUserConditionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditUserConditionsComponent, NoopAnimationsModule, ReactiveFormsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: ResolverService, useClass: MockResolverService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EditUserConditionsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policy", {
      user: ["testuser"],
      realm: ["realm1"],
      resolver: ["resolver1"],
      user_case_insensitive: false
    });
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit edits when selecting realms", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.selectRealm(["realm2"]);
    expect(spy).toHaveBeenCalledWith({ realm: ["realm2"] });
  });

  it("should add user and clear form", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.addUser("newuser");
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        user: ["testuser", "newuser"]
      })
    );
  });

  it("should toggle user case insensitive state", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.toggleUserCaseInsensitive();
    expect(spy).toHaveBeenCalledWith({ user_case_insensitive: true });
  });

  it("should validate that user does not contain commas", () => {
    component.userFormControl.setValue("user,name");
    expect(component.userFormControl.invalid).toBe(true);
    expect(component.userFormControl.hasError("includesComma")).toBe(true);
  });
});
