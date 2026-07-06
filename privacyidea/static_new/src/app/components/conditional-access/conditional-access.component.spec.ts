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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { ConditionalAccessPolicyService, LockoutPolicy } from "@services/conditional-access/conditional-access-policy.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { MockAuthService, MockConditionalAccessPolicyService, MockTableUtilsService } from "@testing/mock-services";
import { ConditionalAccessComponent } from "./conditional-access.component";

describe("ConditionalAccessComponent", () => {
  let component: ConditionalAccessComponent;
  let fixture: ComponentFixture<ConditionalAccessComponent>;
  let policyServiceMock: MockConditionalAccessPolicyService;
  let router: Router;

  const samplePolicy: LockoutPolicy = {
    id: 1,
    name: "Brute Force",
    time_window_seconds: 600,
    enabled: true,
    dry_run: false,
    priority: 1,
    counter_types_to_track: ["PIN_FAIL"],
    stages: [{ failure_threshold: 5, priority: 1, actions: [] }]
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    policyServiceMock = TestBed.inject(ConditionalAccessPolicyService) as unknown as MockConditionalAccessPolicyService;
    policyServiceMock.policies.set([samplePolicy]);

    fixture = TestBed.createComponent(ConditionalAccessComponent);
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display policies from the service", () => {
    expect(component.policyDataSource().data.length).toBe(1);
    expect(component.policyDataSource().data[0].name).toBe("Brute Force");
  });

  it("should filter by name and by tracked event type", () => {
    component.onFilterInput("brute");
    expect(component.policyDataSource().filter).toBe("brute");
    component.resetFilter();
    expect(component.filterString()).toBe("");
    expect(component.policyDataSource().filter).toBe("");
  });

  it("should navigate to the create page", () => {
    component.onCreatePolicy();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_NEW);
  });

  it("should navigate to the edit page for a policy", () => {
    component.onEditPolicy(samplePolicy);
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_DETAILS + samplePolicy.id);
  });

  it("should disable an enabled policy on toggle", () => {
    component.onToggleEnabled(samplePolicy);
    expect(policyServiceMock.disablePolicy).toHaveBeenCalledWith(1);
  });

  it("should enable a disabled policy on toggle", () => {
    component.onToggleEnabled({ ...samplePolicy, enabled: false });
    expect(policyServiceMock.enablePolicy).toHaveBeenCalledWith(1);
  });

  it("should call deleteWithConfirmDialog on delete", async () => {
    await component.onDeletePolicy(samplePolicy);
    expect(policyServiceMock.deleteWithConfirmDialog).toHaveBeenCalledWith(samplePolicy);
  });
});
