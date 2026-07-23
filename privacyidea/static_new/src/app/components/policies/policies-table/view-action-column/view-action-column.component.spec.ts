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
import { PolicyService } from "@services/policies/policies.service";
import { ViewActionColumnComponent } from "./view-action-column.component";

describe("ViewActionColumnComponent", () => {
  let component: ViewActionColumnComponent;
  let fixture: ComponentFixture<ViewActionColumnComponent>;
  let mockPolicyService: { getDetailsOfAction: jest.Mock };

  beforeEach(async () => {
    mockPolicyService = {
      getDetailsOfAction: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [ViewActionColumnComponent],
      providers: [{ provide: PolicyService, useValue: mockPolicyService }]
    }).compileComponents();

    fixture = TestBed.createComponent(ViewActionColumnComponent);
    component = fixture.componentInstance;
  });

  it("should handle an empty actions object gracefully", () => {
    fixture.componentRef.setInput("actions", {});
    fixture.detectChanges();

    expect(component.actionsList()).toEqual([]);
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector(".action-row")).toBeNull();
  });

  it("should differentiate between boolean and non-boolean actions", () => {
    // Setup metadata: 'otppin' is bool, 'login_mode' is a string
    mockPolicyService.getDetailsOfAction.mockImplementation((name: string) => {
      if (name === "otppin") return { type: "bool" };
      if (name === "login_mode") return { type: "string" };
      return null;
    });

    fixture.componentRef.setInput("actions", {
      otppin: true,
      login_mode: "privacy"
    });
    fixture.detectChanges();

    const list = component.actionsList();

    const otppin = list.find((a) => a.name === "otppin");
    const loginMode = list.find((a) => a.name === "login_mode");

    expect(otppin?.isBoolean).toBe(true);
    expect(loginMode?.isBoolean).toBe(false);

    // Verify template rendering: boolean values shouldn't show the 'value' span
    const compiled = fixture.nativeElement as HTMLElement;
    const rows = compiled.querySelectorAll(".action-row");

    // Find row for otppin
    const otppinRow = Array.from(rows).find((r) => r.textContent?.includes("otppin"));
    expect(otppinRow?.querySelector(".action-value")).toBeNull();

    // Find row for login_mode
    const loginRow = Array.from(rows).find((r) => r.textContent?.includes("login_mode"));
    expect(loginRow?.querySelector(".action-value")).not.toBeNull();
    expect(loginRow?.querySelector(".action-value")?.textContent).toBe("privacy");
  });

  it("should handle missing action metadata gracefully", () => {
    // Service returns null for unknown action
    mockPolicyService.getDetailsOfAction.mockReturnValue(null);

    fixture.componentRef.setInput("actions", { unknown_action: "some_value" });
    fixture.detectChanges();

    const list = component.actionsList();
    expect(list[0].isBoolean).toBe(false); // Default to false if metadata missing
    expect(list[0].value).toBe("some_value");
  });

  it("should update the list when the actions input changes", () => {
    fixture.componentRef.setInput("actions", { initial: "val" });
    fixture.detectChanges();
    expect(component.actionsList().length).toBe(1);

    fixture.componentRef.setInput("actions", { new1: "a", new2: "b" });
    fixture.detectChanges();
    expect(component.actionsList().length).toBe(2);
    expect(component.actionsList()[0].name).toBe("new1");
  });

  it("should pass scope to getDetailsOfAction", () => {
    fixture.componentRef.setInput("actions", { container_add_token: true });
    fixture.componentRef.setInput("scope", "admin");
    fixture.detectChanges();

    expect(mockPolicyService.getDetailsOfAction).toHaveBeenCalledWith("container_add_token", "admin");
  });

  it("should pass undefined scope to getDetailsOfAction when no scope is set", () => {
    fixture.componentRef.setInput("actions", { container_add_token: true });
    fixture.detectChanges();

    expect(mockPolicyService.getDetailsOfAction).toHaveBeenCalledWith("container_add_token", undefined);
  });

  it("keeps the original order when no highlight terms are set", () => {
    mockPolicyService.getDetailsOfAction.mockReturnValue({ type: "str" });
    fixture.componentRef.setInput("actions", { alpha: "1", beta: "2", gamma: "3" });
    fixture.detectChanges();

    expect(component.actionsList().map((a) => a.name)).toEqual(["alpha", "beta", "gamma"]);
  });

  it("floats entries matching a term to the top, preserving order within each group", () => {
    mockPolicyService.getDetailsOfAction.mockReturnValue({ type: "str" });
    fixture.componentRef.setInput("actions", { alpha: "1", beta: "match-here", gamma: "3", delta: "matched" });
    fixture.componentRef.setInput("highlightTerms", ["match"]);
    fixture.detectChanges();

    // beta and delta match (by value); alpha and gamma keep their relative order after them.
    expect(component.actionsList().map((a) => a.name)).toEqual(["beta", "delta", "alpha", "gamma"]);
  });

  it("matches on the action name as well as the value", () => {
    mockPolicyService.getDetailsOfAction.mockReturnValue({ type: "str" });
    fixture.componentRef.setInput("actions", { alpha: "1", login_mode: "x" });
    fixture.componentRef.setInput("highlightTerms", ["login"]);
    fixture.detectChanges();

    expect(component.actionsList()[0].name).toBe("login_mode");
  });

  it("does not float a boolean action whose only match is its hidden value", () => {
    mockPolicyService.getDetailsOfAction.mockImplementation((name: string) =>
      name === "flag" ? { type: "bool" } : { type: "str" }
    );
    fixture.componentRef.setInput("actions", { alpha: "1", flag: true });
    fixture.componentRef.setInput("highlightTerms", ["true"]);
    fixture.detectChanges();

    // The boolean value is not rendered, so it must not reorder to the top.
    expect(component.actionsList().map((a) => a.name)).toEqual(["alpha", "flag"]);
  });

  it("should resolve correct isBoolean per scope", () => {
    mockPolicyService.getDetailsOfAction.mockImplementation((name: string, scope: string) => {
      if (scope === "admin" && name === "container_add_token") return { type: "bool" };
      if (scope === "user" && name === "container_add_token") return { type: "str" };
      return null;
    });

    fixture.componentRef.setInput("actions", { container_add_token: true });

    fixture.componentRef.setInput("scope", "admin");
    fixture.detectChanges();
    expect(component.actionsList()[0].isBoolean).toBe(true);

    fixture.componentRef.setInput("scope", "user");
    fixture.detectChanges();
    expect(component.actionsList()[0].isBoolean).toBe(false);
  });
});
