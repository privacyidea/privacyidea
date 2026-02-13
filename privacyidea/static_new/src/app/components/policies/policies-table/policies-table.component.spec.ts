/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { PoliciesTableComponent } from "./policies-table.component";
import { PolicyService, PolicyDetail } from "../../../services/policies/policies.service";
import { DialogService } from "../../../services/dialog/dialog.service";
import { AuthService } from "../../../services/auth/auth.service";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { Component, Input, output } from "@angular/core";
import { FilterValueGeneric } from "../../../core/models/filter_value_generic/filter-value-generic";
import { MockPolicyService } from "src/testing/mock-services/mock-policies-service";
import { MockDialogService } from "src/testing/mock-services/mock-dialog-service";
import { MockAuthService } from "src/testing/mock-services/mock-auth-service";
import { MockTableUtilsService } from "src/testing/mock-services/mock-table-utils-service";

@Component({ selector: "app-policy-filter", template: "", standalone: true })
class MockPolicyFilterComponent {
  @Input() initialFilter!: FilterValueGeneric<any>;
  @Input() unfilteredPolicies!: any[];
  filterChange = output<FilterValueGeneric<any>>();
  updateFilterManually = jest.fn();
  focusInput = jest.fn();
}

describe("PoliciesTableComponent", () => {
  let component: PoliciesTableComponent;
  let fixture: ComponentFixture<PoliciesTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PoliciesTableComponent],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    })
      .overrideComponent(PoliciesTableComponent, {
        set: { imports: [MockPolicyFilterComponent] }
      })
      .compileComponents();

    fixture = TestBed.createComponent(PoliciesTableComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("isFiltered", false);
    fixture.detectChanges();
  });

  it("should update filter signal when onFilterUpdate is called", () => {
    const newFilter = new FilterValueGeneric<PolicyDetail>({ availableFilters: [] });
    component.onFilterUpdate(newFilter);
    expect(component.filter()).toBe(newFilter);
  });
});
