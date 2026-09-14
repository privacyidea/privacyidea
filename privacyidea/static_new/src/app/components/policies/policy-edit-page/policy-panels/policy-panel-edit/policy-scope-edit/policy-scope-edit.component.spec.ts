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
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { PolicyService } from "@services/policies/policies.service";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { PolicyScopeEditComponent } from "./policy-scope-edit.component";

describe("PolicyScopeEditComponent", () => {
  let component: PolicyScopeEditComponent;
  let fixture: ComponentFixture<PolicyScopeEditComponent>;
  let policyService: MockPolicyService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PolicyScopeEditComponent],
      providers: [{ provide: PolicyService, useClass: MockPolicyService }]
    }).compileComponents();

    fixture = TestBed.createComponent(PolicyScopeEditComponent);
    component = fixture.componentInstance;
    policyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    (policyService.allPolicyScopes as unknown as { set: (value: string[]) => void }).set(["admin", "user", "webui"]);
    fixture.componentRef.setInput("scope", "user");
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should offer every scope plus the all-scopes option", () => {
    const select = fixture.debugElement.query(By.directive(MatSelect));
    select.componentInstance.open();
    fixture.detectChanges();

    const options = fixture.debugElement.queryAll(By.css("mat-option"));
    expect(options.map((option) => option.componentInstance.value)).toEqual(["", "admin", "user", "webui"]);
    expect(select.componentInstance.value).toBe("user");
  });

  it("should emit the picked scope", () => {
    const spy = jest.spyOn(component.scopeChange, "emit");
    const select = fixture.debugElement.query(By.directive(MatSelect));
    select.componentInstance.open();
    fixture.detectChanges();

    const options = fixture.debugElement.queryAll(By.css("mat-option"));
    options.find((option) => option.componentInstance.value === "admin")!.nativeElement.click();
    fixture.detectChanges();

    expect(spy).toHaveBeenCalledWith("admin");
  });

  it("should disable the select when the scope is locked", () => {
    fixture.componentRef.setInput("disabled", true);
    fixture.detectChanges();

    const select = fixture.debugElement.query(By.directive(MatSelect));
    expect(select.componentInstance.disabled).toBe(true);
  });
});
