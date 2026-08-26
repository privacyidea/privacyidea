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
import {
  ConditionalAccessPolicyService,
  ConditionTypeMeta,
  ConditionalAccessPolicyCondition
} from "@services/conditional-access/conditional-access-policy.service";
import { MockConditionalAccessPolicyService } from "@testing/mock-services/mock-conditional-access-policy-service";
import { ConditionalAccessConditionsComponent } from "./conditional-access-conditions.component";

const CONDITION_TYPE_META: Record<string, ConditionTypeMeta> = {
  USER_REALM: {
    label: "User realm",
    operators: [
      { name: "IN", label: "is one of" },
      { name: "NOT_IN", label: "is not one of" }
    ],
    choices: ["sales", "support"]
  },
  USER_ROLE: {
    label: "User role",
    operators: [
      { name: "IN", label: "is one of" },
      { name: "NOT_IN", label: "is not one of" }
    ],
    choices: ["admin-external", "admin-internal", "user"]
  }
};

describe("ConditionalAccessConditionsComponent", () => {
  let component: ConditionalAccessConditionsComponent;
  let fixture: ComponentFixture<ConditionalAccessConditionsComponent>;
  let policyServiceMock: MockConditionalAccessPolicyService;

  const setConditions = (conditions: ConditionalAccessPolicyCondition[]): void => {
    fixture.componentRef.setInput("conditions", conditions);
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessConditionsComponent],
      providers: [{ provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService }]
    }).compileComponents();

    policyServiceMock = TestBed.inject(ConditionalAccessPolicyService) as unknown as MockConditionalAccessPolicyService;
    policyServiceMock.conditionTypes.set(CONDITION_TYPE_META);

    fixture = TestBed.createComponent(ConditionalAccessConditionsComponent);
    fixture.componentRef.setInput("conditions", []);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  const renderedLabels = (): string[] =>
    Array.from(fixture.nativeElement.querySelectorAll(".ca-condition-label")).map((label) =>
      (label as HTMLElement).textContent!.trim()
    );

  it("should render a row per served condition type, labelled by the backend", () => {
    expect(renderedLabels()).toEqual(["User realm", "User role"]);
  });

  // The point of driving the rows off the endpoint: the backend registry is designed so a new
  // condition kind is a registry entry, and it must not need a WebUI change to become usable.
  it("should render a condition type the WebUI does not know, with generic wording", () => {
    policyServiceMock.conditionTypes.set({
      ...CONDITION_TYPE_META,
      CLIENT_LABEL: { label: "Client label", operators: [{ name: "IN", label: "is one of" }], choices: ["kiosk"] }
    });
    fixture.detectChanges();
    expect(renderedLabels()).toEqual(["User realm", "User role", "Client label"]);

    const unknownRow = component.rows()[2];
    expect(unknownRow.valuesLabel).toBe("Client label");
    expect(component.hintFor(unknownRow)).toBe("Restrict the values this policy is applied to.");
  });

  // A multi-select cannot represent an open value space, so offering an empty one would be worse than
  // offering nothing at all.
  it("should skip a condition type whose values cannot be enumerated", () => {
    policyServiceMock.conditionTypes.set({
      USER_REALM: CONDITION_TYPE_META["USER_REALM"],
      HTTP_HEADER: { label: "HTTP header", operators: [{ name: "IN", label: "is one of" }], choices: null }
    });
    fixture.detectChanges();
    expect(renderedLabels()).toEqual(["User realm"]);
  });

  // Otherwise a stored condition would be invisible while still being saved with the policy.
  it("should render a type the policy carries even when the endpoint does not offer it", () => {
    policyServiceMock.conditionTypes.set({});
    setConditions([{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }]);
    expect(renderedLabels()).toEqual(["USER_REALM"]);
    expect(component.selectedValues("USER_REALM")).toEqual(["sales"]);
  });

  it("should not render a type twice when the policy carries one the endpoint also offers", () => {
    setConditions([{ condition_type: "USER_ROLE", operator: "IN", value: ["user"] }]);
    expect(renderedLabels()).toEqual(["User realm", "User role"]);
  });

  it("should default a type without a condition to IN and no selected values", () => {
    expect(component.selectedOperator("USER_REALM")).toBe("IN");
    expect(component.selectedValues("USER_REALM")).toEqual([]);
  });

  it("should read the operator and values from an existing condition", () => {
    setConditions([{ condition_type: "USER_REALM", operator: "NOT_IN", value: ["sales"] }]);
    expect(component.selectedOperator("USER_REALM")).toBe("NOT_IN");
    expect(component.selectedValues("USER_REALM")).toEqual(["sales"]);
  });

  it("should add a condition carrying the current operator when values are picked", () => {
    const spy = jest.spyOn(component.conditionsChange, "emit");
    component.onValuesChange("USER_REALM", ["sales", "support"]);
    expect(spy).toHaveBeenCalledWith([{ condition_type: "USER_REALM", operator: "IN", value: ["sales", "support"] }]);
  });

  // Without the pending-operator state the choice would be lost: a row with no values emits no
  // condition, so there is nowhere in the policy to keep the operator until values arrive.
  it("should keep an operator picked before any value was selected", () => {
    component.onOperatorChange("USER_REALM", "NOT_IN");
    expect(component.selectedOperator("USER_REALM")).toBe("NOT_IN");

    const spy = jest.spyOn(component.conditionsChange, "emit");
    component.onValuesChange("USER_REALM", ["sales"]);
    expect(spy).toHaveBeenCalledWith([{ condition_type: "USER_REALM", operator: "NOT_IN", value: ["sales"] }]);
  });

  it("should not emit on an operator change while the type carries no condition", () => {
    const spy = jest.spyOn(component.conditionsChange, "emit");
    component.onOperatorChange("USER_REALM", "NOT_IN");
    expect(spy).not.toHaveBeenCalled();
  });

  // The stored operator has to win over the remembered one, or loading a policy into an instance
  // where an operator was picked for an empty row would display an operator the policy does not have.
  it("should show the loaded condition's operator over a previously remembered one", () => {
    component.onOperatorChange("USER_REALM", "NOT_IN");
    setConditions([{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }]);
    expect(component.selectedOperator("USER_REALM")).toBe("IN");
  });

  it("should replace the operator of an existing condition, keeping its values", () => {
    setConditions([{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }]);
    const spy = jest.spyOn(component.conditionsChange, "emit");
    component.onOperatorChange("USER_REALM", "NOT_IN");
    expect(spy).toHaveBeenCalledWith([{ condition_type: "USER_REALM", operator: "NOT_IN", value: ["sales"] }]);
  });

  it("should replace the values of an existing condition, keeping its operator", () => {
    setConditions([{ condition_type: "USER_REALM", operator: "NOT_IN", value: ["sales"] }]);
    const spy = jest.spyOn(component.conditionsChange, "emit");
    component.onValuesChange("USER_REALM", ["support"]);
    expect(spy).toHaveBeenCalledWith([{ condition_type: "USER_REALM", operator: "NOT_IN", value: ["support"] }]);
  });

  // The backend rejects an empty value list, so "no restriction" has to be the absence of the
  // condition rather than a condition with nothing in it.
  it("should remove the condition when its last value is deselected", () => {
    setConditions([
      { condition_type: "USER_REALM", operator: "IN", value: ["sales"] },
      { condition_type: "USER_ROLE", operator: "IN", value: ["user"] }
    ]);
    const spy = jest.spyOn(component.conditionsChange, "emit");
    component.onValuesChange("USER_REALM", []);
    expect(spy).toHaveBeenCalledWith([{ condition_type: "USER_ROLE", operator: "IN", value: ["user"] }]);
  });

  it("should offer a clear button only for a row that has a selection", () => {
    expect(fixture.nativeElement.querySelectorAll("app-clear-button").length).toBe(0);
    setConditions([{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }]);
    expect(fixture.nativeElement.querySelectorAll("app-clear-button").length).toBe(1);
  });

  it("should remove the condition when its clear button is pressed", () => {
    setConditions([{ condition_type: "USER_REALM", operator: "IN", value: ["sales", "support"] }]);
    const spy = jest.spyOn(component.conditionsChange, "emit");
    fixture.nativeElement.querySelector("app-clear-button button").click();
    expect(spy).toHaveBeenCalledWith([]);
  });

  it("should keep the other condition untouched when replacing one of two", () => {
    setConditions([
      { condition_type: "USER_REALM", operator: "IN", value: ["sales"] },
      { condition_type: "USER_ROLE", operator: "IN", value: ["user"] }
    ]);
    const spy = jest.spyOn(component.conditionsChange, "emit");
    component.onValuesChange("USER_REALM", ["support"]);
    expect(spy).toHaveBeenCalledWith([
      { condition_type: "USER_REALM", operator: "IN", value: ["support"] },
      { condition_type: "USER_ROLE", operator: "IN", value: ["user"] }
    ]);
  });

  // Emitted in condition_type order, matching how the backend serves them: appending in edit order
  // would let "remove then re-add" reorder the array, which the edit page's JSON diff would read as
  // an unsaved change even though the conditions are identical (they are ANDed, so order is nothing).
  it("should emit a newly added condition in condition_type order, not appended", () => {
    setConditions([{ condition_type: "USER_ROLE", operator: "IN", value: ["user"] }]);
    const spy = jest.spyOn(component.conditionsChange, "emit");
    component.onValuesChange("USER_REALM", ["sales"]);
    expect(spy).toHaveBeenCalledWith([
      { condition_type: "USER_REALM", operator: "IN", value: ["sales"] },
      { condition_type: "USER_ROLE", operator: "IN", value: ["user"] }
    ]);
  });

  it("should report no change after a condition is removed and re-added", () => {
    const original: ConditionalAccessPolicyCondition[] = [
      { condition_type: "USER_REALM", operator: "IN", value: ["sales"] },
      { condition_type: "USER_ROLE", operator: "IN", value: ["user"] }
    ];
    setConditions(original);

    // Clear the realm row, feed the result back in as the parent would, then re-add it.
    const spy = jest.spyOn(component.conditionsChange, "emit");
    component.onValuesChange("USER_REALM", []);
    setConditions(spy.mock.calls[0][0]);
    component.onValuesChange("USER_REALM", ["sales"]);

    expect(spy.mock.calls[1][0]).toEqual(original);
  });

  it("should offer the backend's choices plus any value the policy references that is gone", () => {
    setConditions([{ condition_type: "USER_REALM", operator: "IN", value: ["sales", "deleted"] }]);
    expect(component.valueOptions("USER_REALM")).toEqual(["sales", "support", "deleted"]);
    expect(component.isStaleValue("USER_REALM", "deleted")).toBe(true);
    expect(component.isStaleValue("USER_REALM", "sales")).toBe(false);
    expect(component.staleValuesFor("USER_REALM")).toEqual(["deleted"]);
  });

  it("should show the stale-value warning and hide it once the value is removed", () => {
    setConditions([{ condition_type: "USER_REALM", operator: "IN", value: ["deleted"] }]);
    expect(fixture.nativeElement.querySelector(".ca-condition-stale")).toBeTruthy();

    setConditions([{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }]);
    expect(fixture.nativeElement.querySelector(".ca-condition-stale")).toBeNull();
  });

  // Before /conditiontypes answers there is no vocabulary to judge against, so nothing may be
  // called unknown - otherwise every value would flash as broken on first paint.
  it("should treat no loaded vocabulary as nothing being stale", () => {
    policyServiceMock.conditionTypes.set({});
    setConditions([{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }]);
    expect(component.staleValuesFor("USER_REALM")).toEqual([]);
    expect(component.valueOptions("USER_REALM")).toEqual(["sales"]);
  });

  it("should fall back to its own operator labels until the vocabulary loads", () => {
    policyServiceMock.conditionTypes.set({});
    fixture.detectChanges();
    expect(component.operatorOptions("USER_REALM").map((operator) => operator.name)).toEqual(["IN", "NOT_IN"]);
  });

  // The same selection restricts under IN and exempts under NOT_IN, so the hint has to follow the
  // operator - and it stays visible either way, unlike the stale-value warning that replaces it.
  it("should show a hint that follows the operator, selected or not", () => {
    const [realmRow] = component.rows();
    expect(component.hintFor(realmRow)).toBe("Restrict the realms this policy is applied to.");

    component.onOperatorChange("USER_REALM", "NOT_IN");
    expect(component.hintFor(realmRow)).toBe("Exclude realms from this policy.");

    setConditions([{ condition_type: "USER_REALM", operator: "NOT_IN", value: ["sales"] }]);
    expect(fixture.nativeElement.querySelector("mat-hint").textContent.trim()).toBe("Exclude realms from this policy.");
  });

  // The operator is whatever the backend served, so the wording table can be missing an entry for it.
  // Before the types were widened this indexed a union-keyed record and rendered a blank hint.
  it("should fall back to a neutral hint for an operator it has no wording for", () => {
    policyServiceMock.conditionTypes.set({
      USER_REALM: {
        label: "User realm",
        operators: [{ name: "MATCHES", label: "matches" }],
        choices: ["sales"]
      }
    });
    setConditions([{ condition_type: "USER_REALM", operator: "MATCHES", value: ["sales"] }]);
    expect(component.hintFor(component.rows()[0])).toBe("The values this condition compares against.");
  });

  it("should show friendly labels for roles but realm names verbatim", () => {
    const [realmRow, roleRow] = component.rows();
    expect(component.valueLabel(realmRow, "sales")).toBe("sales");
    expect(component.valueLabel(roleRow, "admin-internal")).toBe("Administrator (internal)");
  });
});
