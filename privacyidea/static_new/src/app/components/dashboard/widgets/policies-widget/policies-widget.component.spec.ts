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
import { provideZonelessChangeDetection } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { DASHBOARD_COLUMNS, DashboardWidget, WidgetInstance } from "@models/dashboard";
import { AuthService } from "@services/auth/auth.service";
import { PolicyDetail, PolicyService } from "@services/policies/policies.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockPiResponse } from "@testing/mock-services/mock-utils";
import { MockPolicyService } from "@testing/mock-services/mock-policies-service";
import { of } from "rxjs";
import { PoliciesWidgetComponent } from "./policies-widget.component";

describe("PoliciesWidgetComponent", () => {
  let fixture: ComponentFixture<PoliciesWidgetComponent>;
  let component: PoliciesWidgetComponent;
  let authMock: MockAuthService;
  let policyMock: MockPolicyService;

  const instance: WidgetInstance = { id: "policies-1", type: "policies", x: 0, y: 0, cols: 8, rows: 5 };

  const mockPolicies = [
    { name: "pol-active-1", active: true },
    { name: "pol-active-2", active: true },
    { name: "pol-inactive-1", active: false }
  ] as PolicyDetail[];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PoliciesWidgetComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
        { provide: PolicyService, useClass: MockPolicyService }
      ]
    }).compileComponents();

    authMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: ["policyread"] });

    policyMock = TestBed.inject(PolicyService) as unknown as MockPolicyService;
    policyMock.getPolicies.mockReturnValue(of(MockPiResponse.fromValue<PolicyDetail[]>(mockPolicies)));

    fixture = TestBed.createComponent(PoliciesWidgetComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("instance", instance);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should extend the DashboardWidget base", () => {
    expect(component).toBeInstanceOf(DashboardWidget);
  });

  it("should override the static metadata", () => {
    expect(PoliciesWidgetComponent.type).toBe("policies");
    expect(PoliciesWidgetComponent.title).toBeTruthy();
    expect(PoliciesWidgetComponent.icon).toBe("gavel");
  });

  it("should override the static size constraints", () => {
    expect(PoliciesWidgetComponent.defaultSize).toEqual({ cols: 10, rows: 5 });
    expect(PoliciesWidgetComponent.minSize).toEqual({ cols: 6, rows: 5 });
    expect(PoliciesWidgetComponent.maxSize).toEqual({ cols: DASHBOARD_COLUMNS, rows: 8 });
  });

  it("should render the active and inactive counts", () => {
    const cells = fixture.nativeElement.querySelectorAll("td:last-child");
    const values = Array.from(cells).map((td: Element) => td.textContent?.trim());
    expect(values).toContain("2");
    expect(values).toContain("1");
  });

  it("should render active policy names as links", () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain("pol-active-1");
    expect(text).toContain("pol-active-2");
  });

  it("should render inactive policy names as links", () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain("pol-inactive-1");
  });

  it("should render Active Policies and Inactive Policies labels", () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain("Active Policies");
    expect(text).toContain("Inactive Policies");
  });

  it("should render nothing when policyread right is missing", async () => {
    authMock.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights: [] });

    const fixture2 = TestBed.createComponent(PoliciesWidgetComponent);
    fixture2.componentRef.setInput("instance", instance);
    fixture2.detectChanges();

    expect(fixture2.nativeElement.querySelector("table")).toBeNull();
    fixture2.destroy();
  });
});
