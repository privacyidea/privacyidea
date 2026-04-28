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
import { AuthService } from "../../../services/auth/auth.service";
import { DialogService } from "src/app/services/dialog/dialog.service";
import { Component, Input, output } from "@angular/core";
import { By } from "@angular/platform-browser";
import { of } from "rxjs";
import { FilterValueGeneric } from "src/app/core/models/filter_value_generic/filter-value-generic";
import { PolicyDetail, PolicyService } from "src/app/services/policies/policies.service";
import { TableUtilsService } from "src/app/services/table-utils/table-utils.service";
import { MockDialogService, MockPolicyService, MockRouter, MockTableUtilsService } from "src/testing/mock-services";
import { MockAuthService } from "src/testing/mock-services/mock-auth-service";
import { PoliciesTableComponent } from "./policies-table.component";
import { PolicyFilterComponent } from "./policy-filter/policy-filter.component";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "../../../route_paths";

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
  let mockPolicyService: MockPolicyService;
  let mockDialogService: MockDialogService;
  let router: MockRouter;

  const mockPolicies: PolicyDetail[] = [
    { name: "Policy-C", priority: 30, scope: "admin", active: true } as PolicyDetail,
    { name: "Policy-A", priority: 10, scope: "user", active: false } as PolicyDetail,
    { name: "Policy-B", priority: 20, scope: "all", active: true } as PolicyDetail
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PoliciesTableComponent, NoopAnimationsModule],
      providers: [
        { provide: PolicyService, useClass: MockPolicyService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: PolicyFilterComponent, useClass: MockPolicyFilterComponent },
        { provide: Router, useClass: MockRouter }
      ]
    })
      .overrideComponent(PoliciesTableComponent, {
        remove: { imports: [PolicyFilterComponent] },
        add: { imports: [MockPolicyFilterComponent] }
      })
      .compileComponents();

    mockPolicyService = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    mockDialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router) as unknown as MockRouter;

    mockPolicyService.allPolicies.set(mockPolicies);

    fixture = TestBed.createComponent(PoliciesTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should show skeleton rows when service returns no policies", () => {
    mockPolicyService.allPolicies.set([]);
    fixture.detectChanges();

    const rows = fixture.debugElement.queryAll(By.css("tr[mat-row]"));

    expect(rows.length).toBe(component.skeletonRowCount);
    expect(rows[0].classes["skeleton-row"]).toBeTruthy();
  });

  it("should disable header checkbox when in skeleton state", () => {
    mockPolicyService.allPolicies.set([]);
    fixture.detectChanges();

    const headerCheckbox = fixture.debugElement.query(By.css("th.mat-column-select mat-checkbox"));
    expect(headerCheckbox.componentInstance.disabled).toBeTruthy();
  });

  it("should display all rows when policies are present", () => {
    fixture.detectChanges();

    const displayedRows = fixture.debugElement.queryAll(By.css("tr[mat-row], mat-row, .mat-mdc-row"));
    expect(displayedRows.length).toBe(3);
    expect(component.sortedFilteredPolicies().length).toBe(3);
  });

  it("should select all displayed rows when masterToggle is called", () => {
    fixture.detectChanges();

    component.masterToggle();
    expect(component.selectedPolicies().size).toBe(3);
    expect(component.selectedPolicies().has("Policy-A")).toBeTruthy();
    expect(component.selectedPolicies().has("Policy-B")).toBeTruthy();
    expect(component.selectedPolicies().has("Policy-C")).toBeTruthy();
  });

  it("should open edit dialog only if row is not a skeleton row", () => {
    const dialogSpy = jest.spyOn(mockDialogService, "openDialog").mockReturnValue({
      afterClosed: () => of(null)
    } as any);

    component.editPolicy(mockPolicies[0]);
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_DETAILS + mockPolicies[0].name);

    jest.clearAllMocks();
    component.editPolicy({ name: "" } as PolicyDetail);
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  it("should filter items", () => {
    const newFilter = component.filter().setValueOfKey("name", "Policy-A");
    component.filter.set(newFilter);
    fixture.detectChanges();

    const rows = fixture.debugElement.queryAll(By.css("tr[mat-row], mat-row, .mat-mdc-row"));
    expect(rows.length).toBe(1);
  });

  it("should show 'no data' row when filter matches nothing and policies exist", () => {
    const newFilter = component.filter().setValueOfKey("name", "NonExistent");
    component.filter.set(newFilter);
    fixture.detectChanges();

    const noDataRow = fixture.debugElement.query(By.css("tr.mat-mdc-no-data-row"));
    expect(noDataRow).toBeTruthy();
    expect(noDataRow.nativeElement.textContent).toContain($localize`No data matching the filter.`);
  });

  it("should toggle filter keys when clicking header filter buttons", () => {
    const filterButton = fixture.debugElement.query(By.css(".col-name .filter-button"));

    filterButton.nativeElement.click();
    fixture.detectChanges();

    expect(component.filter().hasKey("name")).toBeTruthy();

    filterButton.nativeElement.click();
    fixture.detectChanges();

    expect(component.filter().hasKey("name")).toBeFalsy();
  });

  it("should return correct icon names for different filter action types", () => {
    expect(component.getFilterIconName("name")).toBe("filter_alt");

    const activeFilter = component.filter().toggleKey("name");
    component.filter.set(activeFilter);

    expect(component.getFilterIconName("name")).toBe("filter_alt_off");
  });

  it("should sort data by priority ascending", () => {
    component.onSortChange({ active: "priority", direction: "asc" });
    fixture.detectChanges();

    const data = component.sortedFilteredPolicies();
    expect(data[0].name).toBe("Policy-A");
    expect(data[1].name).toBe("Policy-B");
    expect(data[2].name).toBe("Policy-C");
  });

  it("should sort data by priority descending", () => {
    component.onSortChange({ active: "priority", direction: "desc" });
    fixture.detectChanges();

    const data = component.sortedFilteredPolicies();
    expect(data[0].name).toBe("Policy-C");
    expect(data[1].name).toBe("Policy-B");
    expect(data[2].name).toBe("Policy-A");
  });

  it("should return unsorted data if sort direction is empty", () => {
    component.onSortChange({ active: "priority", direction: "" });
    fixture.detectChanges();

    const data = component.sortedFilteredPolicies();
    // Default initial order from mock
    expect(data[0].name).toBe("Policy-C");
  });

  it("should have the correct colspan in the 'no data' row based on columnKeys", () => {
    const newFilter = component.filter().setValueOfKey("name", "NonExistent");
    component.filter.set(newFilter);
    fixture.detectChanges();

    const noDataCell = fixture.debugElement.query(By.css("tr.mat-mdc-no-data-row td"));
    const expectedColspan = component.columnKeys().length;

    expect(noDataCell.attributes["colspan"]).toBe(expectedColspan.toString());
  });
});
