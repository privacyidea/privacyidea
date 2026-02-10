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
import { ReactiveFormsModule } from "@angular/forms";
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { PolicyService } from "src/app/services/policies/policies.service";
import { RealmService } from "src/app/services/realm/realm.service";
import { ResolverService } from "src/app/services/resolver/resolver.service";
import { MockRealmService } from "src/testing/mock-services";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { MockResolverService } from "src/testing/mock-services/mock-resolver-service";
import { EditAdminConditionsComponent } from "./edit-admin-conditions.component";

describe("EditAdminConditionsComponent", () => {
  let component: EditAdminConditionsComponent;
  let fixture: ComponentFixture<EditAdminConditionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditAdminConditionsComponent, ReactiveFormsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: RealmService, useClass: MockRealmService },
        { provide: ResolverService, useClass: MockResolverService },
        provideNoopAnimations()
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EditAdminConditionsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("policy", {
      adminuser: ["admin1"],
      adminrealm: ["realm1"]
    });
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should add admin user and clear input", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.addAdmin("admin2");
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        adminuser: ["admin1", "admin2"]
      })
    );
    expect(component.adminFormControl.value).toBe("");
  });

  it("should remove admin user", () => {
    const spy = jest.spyOn(component.policyEdit, "emit");
    component.removeAdmin("admin1");
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        adminuser: []
      })
    );
  });
});
