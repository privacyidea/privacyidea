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

import { Component, Input, output } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatDialogRef } from "@angular/material/dialog";
import { By } from "@angular/platform-browser";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { PoliciesTableComponent } from "@components/policies/policies-table/policies-table.component";
import { PolicyFilterComponent } from "@components/policies/policies-table/policy-filter/policy-filter.component";
import { FilterValueGeneric } from "@core/models/filter_value_generic/filter-value-generic";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockDialogService, MockPolicyService, MockRouter, MockTableUtilsService } from "@testing/mock-services";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { of } from "rxjs";

@Component({ selector: "app-policy-filter", template: "", standalone: true })
class MockPolicyFilterComponent {
  @Input() initialFilter!: FilterValueGeneric<PolicyDetail>;
  @Input() unfilteredPolicies!: PolicyDetail[];
  filterChange = output<FilterValueGeneric<PolicyDetail>>();
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
      imports: [PoliciesTableComponent],
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
    jest.spyOn(mockDialogService, "openDialog").mockReturnValue({
      afterClosed: () => of(null)
    } as unknown as MatDialogRef<never, never>);

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

  describe("filter matching and highlighting", () => {
    const richPolicies: PolicyDetail[] = [
      {
        name: "enroll-hotp",
        priority: 10,
        scope: "enrollment",
        active: true,
        description: "handles hotp tokens",
        action: { tokentype: "hotp", max_count: "5" },
        realm: ["sales"],
        user: ["alice"],
        adminrealm: [],
        adminuser: [],
        pinode: [],
        client: ["10.0.0.1"],
        user_agents: [],
        time: "",
        conditions: []
      } as unknown as PolicyDetail,
      {
        name: "auth-totp",
        priority: 20,
        scope: "authentication",
        active: false,
        description: "totp only",
        action: { tokentype: "totp" },
        realm: ["support"],
        user: [],
        adminrealm: [],
        adminuser: [],
        pinode: [],
        client: [],
        user_agents: [],
        time: "Mon-Fri: 08:00-17:00",
        conditions: [["userinfo", "department", "==", "it", true, "raise_error"]]
      } as unknown as PolicyDetail
    ];

    beforeEach(() => {
      mockPolicyService.allPolicies.set(richPolicies);
      fixture.detectChanges();
    });

    const filterBy = (value: string) => {
      component.filter.set(component.filter().setByString(value));
      fixture.detectChanges();
      return component.policiesListFiltered().map((p) => p.name);
    };

    it("matches a keyword-less term across all columns", () => {
      expect(filterBy("hotp")).toEqual(["enroll-hotp"]); // action value
      expect(filterBy("sales")).toEqual(["enroll-hotp"]); // condition (realm)
      expect(filterBy("only")).toEqual(["auth-totp"]); // description
      expect(filterBy("enrollment")).toEqual(["enroll-hotp"]); // scope
    });

    it("matches with the actions keyword on names and values", () => {
      expect(filterBy("actions: max_count")).toEqual(["enroll-hotp"]);
      expect(filterBy("actions: totp")).toEqual(["auth-totp"]);
    });

    it("excludes policies without any actions from an actions keyword filter", () => {
      const noActionPolicy = {
        name: "no-actions",
        priority: 30,
        scope: "admin",
        active: true,
        description: "",
        action: undefined,
        realm: [],
        user: [],
        adminrealm: [],
        adminuser: [],
        pinode: [],
        client: [],
        user_agents: [],
        time: "",
        conditions: []
      } as unknown as PolicyDetail;
      mockPolicyService.allPolicies.set([...richPolicies, noActionPolicy]);
      fixture.detectChanges();

      // A policy with no actions must not pass an active `actions:` filter (it matches on the shared
      // "tokentype" action key that both action-bearing policies define).
      expect(filterBy("actions: tokentype")).toEqual(["enroll-hotp", "auth-totp"]);
    });

    it("matches with the conditions keyword across condition fields", () => {
      expect(filterBy("conditions: support")).toEqual(["auth-totp"]);
      expect(filterBy("conditions: department")).toEqual(["auth-totp"]);
      expect(filterBy("conditions: 10.0.0.1")).toEqual(["enroll-hotp"]);
    });

    it("matches with the description keyword", () => {
      expect(filterBy("description: handles")).toEqual(["enroll-hotp"]);
    });

    it("supports priority comparison operators", () => {
      expect(filterBy("priority: >=20")).toEqual(["auth-totp"]);
      expect(filterBy("priority: <=10")).toEqual(["enroll-hotp"]);
      expect(filterBy("priority: >15")).toEqual(["auth-totp"]);
      expect(filterBy("priority: <15")).toEqual(["enroll-hotp"]);
      expect(filterBy("priority: !=10")).toEqual(["auth-totp"]);
      expect(filterBy("priority: =20")).toEqual(["auth-totp"]);
      expect(filterBy("priority: 10")).toEqual(["enroll-hotp"]);
    });

    it("matches with the active keyword", () => {
      expect(filterBy("active: true")).toEqual(["enroll-hotp"]);
      expect(filterBy("active: false")).toEqual(["auth-totp"]);
    });

    it("combines a keyword-less term with a column keyword (AND)", () => {
      expect(filterBy("hotp scope: enrollment")).toEqual(["enroll-hotp"]);
      expect(filterBy("hotp scope: authentication")).toEqual([]);
    });

    it("exposes highlight terms for the dense columns", () => {
      component.filter.set(component.filter().setByString("hotp actions: max_count"));
      fixture.detectChanges();

      const terms = component.highlightTerms();
      expect(terms.actions).toEqual(["hotp", "max_count"]);
      expect(terms.description).toEqual(["hotp"]);
      expect(terms.conditions).toEqual(["hotp"]);
    });
  });
});
