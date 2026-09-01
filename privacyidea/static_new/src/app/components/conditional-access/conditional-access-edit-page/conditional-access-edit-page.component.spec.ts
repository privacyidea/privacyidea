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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActivatedRoute, convertToParamMap, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import {
  ConditionalAccessPolicyService,
  CountMode,
  LockoutActionType,
  LockoutPolicy,
  LockoutPolicySaveParams,
  LockoutTarget
} from "@services/conditional-access/conditional-access-policy.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { SmtpService } from "@services/smtp/smtp.service";
import {
  MockAuthService,
  MockConditionalAccessPolicyService,
  MockNotificationService,
  MockPendingChangesService,
  MockRouter,
  MockSmtpService
} from "@testing/mock-services";
import { BehaviorSubject } from "rxjs";
import { ConditionalAccessEditPageComponent } from "./conditional-access-edit-page.component";

globalThis.IntersectionObserver = class IntersectionObserver {
  disconnect = jest.fn();
  observe = jest.fn();
  unobserve = jest.fn();
  takeRecords = (): IntersectionObserverEntry[] => [];
} as unknown as typeof IntersectionObserver;

const mockPolicy: LockoutPolicy = {
  id: 1,
  name: "Brute Force",
  time_window_seconds: 600,
  enabled: true,
  dry_run: false,
  priority: 1,
  target: "user",
  count_mode: "PER_REQUEST",
  reset_on_success: true,
  counter_types_to_track: ["PIN_FAIL"],
  stages: [{ failure_threshold: 5, priority: 1, actions: [{ action_type: "LOCK_USER", action_value: null }] }],
  conditions: []
};

const EMPTY_TEMPLATE_POLICY: LockoutPolicySaveParams = {
  name: "Password Brute-Force",
  time_window_seconds: 900,
  enabled: true,
  dry_run: false,
  // Templates carry no policy-level priority: the admin must pick a unique one.
  priority: null,
  target: "user",
  count_mode: "PER_REQUEST",
  reset_on_success: true,
  counter_types_to_track: ["PASSWORD_FAIL"],
  stages: [{ failure_threshold: 10, priority: 1, actions: [{ action_type: "LOCK_USER", action_value: null }] }]
};

describe("ConditionalAccessEditPageComponent — edit mode", () => {
  let component: ConditionalAccessEditPageComponent;
  let fixture: ComponentFixture<ConditionalAccessEditPageComponent>;
  let policyServiceMock: MockConditionalAccessPolicyService;
  let pendingChangesServiceMock: MockPendingChangesService;
  let routerMock: MockRouter;
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;

  beforeEach(async () => {
    paramMap$ = new BehaviorSubject(convertToParamMap({ id: String(mockPolicy.id) }));

    await TestBed.configureTestingModule({
      imports: [ConditionalAccessEditPageComponent],
      providers: [
        provideHttpClient(),
        { provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: SmtpService, useClass: MockSmtpService },
        { provide: Router, useClass: MockRouter },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: paramMap$.asObservable(),
            snapshot: { paramMap: convertToParamMap({ id: String(mockPolicy.id) }) }
          }
        }
      ]
    }).compileComponents();

    policyServiceMock = TestBed.inject(ConditionalAccessPolicyService) as unknown as MockConditionalAccessPolicyService;
    pendingChangesServiceMock = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    routerMock = TestBed.inject(Router) as unknown as MockRouter;

    policyServiceMock.policies.set([mockPolicy]);

    fixture = TestBed.createComponent(ConditionalAccessEditPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should load the policy identified by the route param", () => {
    expect(component.isNewPolicy()).toBe(false);
    expect(component.editPolicy().name).toBe("Brute Force");
    expect(component.editPolicy().id).toBe(1);
  });

  it("should show the edit title", () => {
    expect(component.title()).toEqual("Edit Conditional-Access Policy");
  });

  it("should register hasChanges/save/validChanges with PendingChangesService", () => {
    expect(pendingChangesServiceMock.registerHasChanges).toHaveBeenCalled();
    expect(pendingChangesServiceMock.registerSave).toHaveBeenCalled();
    expect(pendingChangesServiceMock.registerValidChanges).toHaveBeenCalled();
  });

  it("should have no changes and be valid right after loading", () => {
    expect(component.hasChanges()).toBe(false);
    expect(component.canSave()).toBe(true);
  });

  it("should detect changes after editing a field", () => {
    component.updateEditPolicy({ time_window_seconds: 900 });
    expect(component.hasChanges()).toBe(true);
  });

  it("should become invalid when the name is cleared", () => {
    component.editPolicy.set({ ...component.editPolicy(), name: "" });
    expect(component.canSave()).toBe(false);
  });

  it("should become invalid when counter_types_to_track is emptied", () => {
    component.onCounterTypesChange([]);
    expect(component.counterTypesValid()).toBe(false);
    expect(component.canSave()).toBe(false);
  });

  it("should become invalid when stages is emptied", () => {
    component.onStagesChange([]);
    expect(component.stagesValid()).toBe(false);
    expect(component.canSave()).toBe(false);
  });

  it("should stay valid when a stage has a zero threshold (an allow/deny allowlist stage)", () => {
    component.onStagesChange([{ failure_threshold: 0, priority: 1, actions: [] }]);
    expect(component.stagesValid()).toBe(true);
  });

  it("should become invalid when a stage has a negative threshold", () => {
    component.onStagesChange([{ failure_threshold: -1, priority: 1, actions: [] }]);
    expect(component.stagesValid()).toBe(false);
  });

  it("should block saving when two stages share a failure threshold", () => {
    component.onStagesChange([
      { failure_threshold: 5, priority: 2, actions: [] },
      { failure_threshold: 5, priority: 1, actions: [] }
    ]);
    expect(component.stageThresholdsUnique()).toBe(false);
    expect(component.canSave()).toBe(false);
    // distinct thresholds are fine
    component.onStagesChange([
      { failure_threshold: 5, priority: 2, actions: [] },
      { failure_threshold: 10, priority: 1, actions: [] }
    ]);
    expect(component.stageThresholdsUnique()).toBe(true);
  });

  it("should update time_window_seconds for valid input only, converting by unit", () => {
    component.onTimeWindowUnitChange("seconds");
    component.onTimeWindowInput("120");
    expect(component.editPolicy().time_window_seconds).toBe(120);
    component.onTimeWindowInput("0");
    expect(component.editPolicy().time_window_seconds).toBe(120);
  });

  it("should convert the entered value to seconds using the selected unit", () => {
    component.onTimeWindowUnitChange("minutes");
    component.onTimeWindowInput("10");
    expect(component.editPolicy().time_window_seconds).toBe(600);
    component.onTimeWindowUnitChange("hours");
    expect(component.editPolicy().time_window_seconds).toBe(36000);
  });

  it("should update priority, clearing to null on empty, non-numeric or decimal input", () => {
    component.onPriorityInput("5");
    expect(component.editPolicy().priority).toBe(5);
    component.onPriorityInput("abc");
    expect(component.editPolicy().priority).toBeNull();
    component.onPriorityInput("");
    expect(component.editPolicy().priority).toBeNull();
    // A decimal must not be silently truncated to a passing integer.
    component.onPriorityInput("1.5");
    expect(component.editPolicy().priority).toBeNull();
  });

  it("should keep the typed text so an invalid priority is explained, not wiped", () => {
    component.onPriorityInput("1.5");
    expect(component.priorityInput()).toBe("1.5");
    expect(component.priorityError()).toBe("not-an-integer");
    component.onPriorityInput("abc");
    expect(component.priorityInput()).toBe("abc");
    expect(component.priorityError()).toBe("not-an-integer");
    // 0 and negatives are out of range, not malformed, but are reported the same way.
    component.onPriorityInput("0");
    expect(component.priorityError()).toBe("not-an-integer");
    component.onPriorityInput("2");
    expect(component.priorityError()).toBeNull();
  });

  it("should distinguish an empty priority from an invalid one", () => {
    component.onPriorityInput("");
    expect(component.priorityError()).toBe("required");
    component.onPriorityInput("   ");
    expect(component.priorityError()).toBe("required");
  });

  it("should show the existing priority in the field in edit mode", () => {
    expect(component.priorityInput()).toBe(String(mockPolicy.priority));
  });

  // mat-form-field only projects <mat-error> while its control is in an error state, so
  // asserting on the signals alone would pass with nothing rendered. These read the DOM.
  const renderedErrors = (): string[] =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map((element) =>
      (element as HTMLElement).textContent!.trim()
    );

  it("should render the priority error message in the DOM, not just compute it", () => {
    component.onPriorityInput("1.5");
    fixture.detectChanges();
    expect(component.priorityError()).toBe("not-an-integer");
    expect(renderedErrors()).toContain("Priority must be a whole number of at least 1.");
  });

  it("should render the required-priority message when the field is cleared", () => {
    component.onPriorityInput("");
    fixture.detectChanges();
    expect(renderedErrors()).toContain("A priority is required.");
  });

  it("should render the collision message naming the conflicting policy", () => {
    policyServiceMock.policies.set([mockPolicy, { ...mockPolicy, id: 99, name: "Other", priority: 4 }]);
    component.onPriorityInput("4");
    fixture.detectChanges();
    expect(component.priorityUnique()).toBe(false);
    expect(renderedErrors().join(" ")).toContain("Other");
  });

  it("should render no priority error for a valid, free priority", () => {
    component.onPriorityInput("42");
    fixture.detectChanges();
    expect(renderedErrors()).toEqual([]);
  });

  it("should toggle dry_run without calling the enable/disable endpoints", () => {
    component.toggleDryRun(true);
    expect(component.editPolicy().dry_run).toBe(true);
    expect(policyServiceMock.enablePolicy).not.toHaveBeenCalled();
    expect(policyServiceMock.disablePolicy).not.toHaveBeenCalled();
  });

  it("should call disablePolicy immediately when toggling enabled off", () => {
    component.toggleEnabled(false);
    expect(component.editPolicy().enabled).toBe(false);
    expect(policyServiceMock.disablePolicy).toHaveBeenCalledWith(1);
  });

  it("should call enablePolicy immediately when toggling enabled on", () => {
    component.toggleEnabled(false);
    component.toggleEnabled(true);
    expect(policyServiceMock.enablePolicy).toHaveBeenCalledWith(1);
  });

  it("should navigate to the list on cancel", () => {
    component.cancelEdit();
    expect(routerMock.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS);
  });

  it("should save and navigate to the list on success", async () => {
    policyServiceMock.savePolicy.mockResolvedValueOnce(1);
    const result = await component.savePolicy();
    expect(result).toBe(true);
    expect(routerMock.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS);
  });

  it("should derive each stage's priority from its threshold on save", async () => {
    policyServiceMock.savePolicy.mockResolvedValueOnce(1);
    component.onStagesChange([
      { failure_threshold: 5, priority: 1, actions: [] },
      { failure_threshold: 10, priority: 1, actions: [] }
    ]);
    await component.savePolicy();
    const payload = policyServiceMock.savePolicy.mock.calls.at(-1)![0];
    expect(payload.stages).toEqual([
      { failure_threshold: 5, priority: 5, actions: [] },
      { failure_threshold: 10, priority: 10, actions: [] }
    ]);
  });

  it("should resolve false and not navigate when save fails", async () => {
    policyServiceMock.savePolicy.mockResolvedValueOnce(undefined);
    routerMock.navigateByUrl.mockClear();
    const result = await component.savePolicy();
    expect(result).toBe(false);
    expect(routerMock.navigateByUrl).not.toHaveBeenCalled();
  });

  it("should delete and navigate to the list", async () => {
    await component.deletePolicy();
    expect(policyServiceMock.deleteWithConfirmDialog).toHaveBeenCalledWith({ id: 1, name: "Brute Force" });
    expect(routerMock.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS);
  });

  describe("conditions", () => {
    beforeEach(() => {
      policyServiceMock.conditionTypes.set({
        USER_REALM: {
          label: "User realm",
          operators: [
            { name: "IN", label: "is one of" },
            { name: "NOT_IN", label: "is not one of" }
          ],
          choices: ["sales", "support"]
        }
      });
    });

    it("should store emitted conditions on the policy", () => {
      component.onConditionsChange([{ condition_type: "USER_REALM", operator: "NOT_IN", value: ["sales"] }]);
      expect(component.editPolicy().conditions).toEqual([
        { condition_type: "USER_REALM", operator: "NOT_IN", value: ["sales"] }
      ]);
      expect(component.hasChanges()).toBe(true);
    });

    // An empty list would stringify differently from an absent key, marking a policy that never had
    // conditions as dirty after a condition was added and removed again.
    it("should drop the key rather than store an empty list, leaving the policy unchanged", () => {
      component.onConditionsChange([{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }]);
      component.onConditionsChange([]);
      expect(component.editPolicy().conditions).toBeUndefined();
      expect(component.hasChanges()).toBe(false);
    });

    it("should not send a conditions key for a policy that has none", async () => {
      await component.savePolicy();
      expect(policyServiceMock.savePolicy).toHaveBeenCalledTimes(1);
      expect(policyServiceMock.savePolicy.mock.calls[0][0]).not.toHaveProperty("conditions");
    });

    it("should send the conditions it has", async () => {
      component.onConditionsChange([{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }]);
      await component.savePolicy();
      expect(policyServiceMock.savePolicy.mock.calls[0][0].conditions).toEqual([
        { condition_type: "USER_REALM", operator: "IN", value: ["sales"] }
      ]);
    });

    // Omitting the key here would leave the stored conditions in place: the backend replaces them
    // only when the key is present, so clearing them takes an explicit empty list.
    it("should send an empty list when the stored policy's last condition is removed", async () => {
      policyServiceMock.policies.set([
        { ...mockPolicy, conditions: [{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }] }
      ]);
      paramMap$.next(convertToParamMap({ id: String(mockPolicy.id) }));
      fixture.detectChanges();

      component.onConditionsChange([]);
      await component.savePolicy();
      expect(policyServiceMock.savePolicy.mock.calls[0][0].conditions).toEqual([]);
    });

    it("should be valid when every condition value still exists", () => {
      component.onConditionsChange([{ condition_type: "USER_REALM", operator: "IN", value: ["sales"] }]);
      expect(component.conditionValuesValid()).toBe(true);
      expect(component.canSave()).toBe(true);
    });

    // The backend rejects a value outside the type's current vocabulary, and the editor PATCHes the
    // whole policy - so without this gate any save of such a policy would fail with a 400.
    it("should be invalid and block saving when a condition names a value that is gone", () => {
      component.onConditionsChange([{ condition_type: "USER_REALM", operator: "IN", value: ["sales", "deleted"] }]);
      expect(component.conditionValuesValid()).toBe(false);
      expect(component.canSave()).toBe(false);
      expect(component.staleConditionValues()).toEqual([{ condition_type: "USER_REALM", values: ["deleted"] }]);
    });

    it("should not block while the condition vocabulary has not loaded", () => {
      policyServiceMock.conditionTypes.set({});
      component.onConditionsChange([{ condition_type: "USER_REALM", operator: "IN", value: ["deleted"] }]);
      expect(component.conditionValuesValid()).toBe(true);
    });

    // Dropping a stale value silently would rewrite the policy on load: dropping it from a NOT_IN
    // widens an exemption and from an IN narrows enforcement, neither of which the admin asked for.
    it("should keep a stale value on the loaded policy instead of dropping it", () => {
      policyServiceMock.policies.set([
        { ...mockPolicy, conditions: [{ condition_type: "USER_REALM", operator: "NOT_IN", value: ["deleted"] }] }
      ]);
      paramMap$.next(convertToParamMap({ id: String(mockPolicy.id) }));
      fixture.detectChanges();
      // toMatchObject rather than toEqual: Signal Forms stamps its own identity symbols onto the
      // objects of the model it wraps, which an exact comparison would trip over.
      expect(component.editPolicy().conditions).toMatchObject([
        { condition_type: "USER_REALM", operator: "NOT_IN", value: ["deleted"] }
      ]);
      expect(component.hasChanges()).toBe(false);
      expect(component.canSave()).toBe(false);
    });
  });
});

describe("ConditionalAccessEditPageComponent — new mode", () => {
  let component: ConditionalAccessEditPageComponent;
  let fixture: ComponentFixture<ConditionalAccessEditPageComponent>;
  let policyServiceMock: MockConditionalAccessPolicyService;

  beforeEach(async () => {
    const paramMap$ = new BehaviorSubject(convertToParamMap({}));

    await TestBed.configureTestingModule({
      imports: [ConditionalAccessEditPageComponent],
      providers: [
        provideHttpClient(),
        { provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: SmtpService, useClass: MockSmtpService },
        { provide: Router, useClass: MockRouter },
        {
          provide: ActivatedRoute,
          useValue: { paramMap: paramMap$.asObservable(), snapshot: { paramMap: convertToParamMap({}) } }
        }
      ]
    }).compileComponents();

    policyServiceMock = TestBed.inject(ConditionalAccessPolicyService) as unknown as MockConditionalAccessPolicyService;
    fixture = TestBed.createComponent(ConditionalAccessEditPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should start empty and invalid (no name, no counter types, no stages)", () => {
    expect(component.isNewPolicy()).toBe(true);
    expect(component.editPolicy().name).toBe("");
    expect(component.canSave()).toBe(false);
  });

  it("should show the create title", () => {
    expect(component.title()).toEqual("Create Conditional-Access Policy");
  });

  it("should not show the enabled toggle affordance calls without an id", () => {
    component.toggleEnabled(true);
    expect(policyServiceMock.enablePolicy).not.toHaveBeenCalled();
    expect(policyServiceMock.disablePolicy).not.toHaveBeenCalled();
  });

  it("should become valid once name, a counter type, a stage and a priority are set", () => {
    component.updateEditPolicy({ name: "New Policy" });
    component.onCounterTypesChange(["PIN_FAIL"]);
    component.onStagesChange([{ failure_threshold: 5, priority: 1, actions: [] }]);
    component.onPriorityInput("1");
    expect(component.canSave()).toBe(true);
  });

  it("should stay invalid until a priority is entered (no default)", () => {
    component.updateEditPolicy({ name: "New Policy" });
    component.onCounterTypesChange(["PIN_FAIL"]);
    component.onStagesChange([{ failure_threshold: 5, priority: 1, actions: [] }]);
    expect(component.editPolicy().priority).toBeNull();
    expect(component.priorityValid()).toBe(false);
    expect(component.canSave()).toBe(false);
    component.onPriorityInput("1");
    expect(component.priorityValid()).toBe(true);
    expect(component.canSave()).toBe(true);
  });

  it("should block saving when the priority collides with an existing policy", () => {
    policyServiceMock.policies.set([{ ...mockPolicy, id: 99, priority: 3 }]);
    component.updateEditPolicy({ name: "New Policy" });
    component.onCounterTypesChange(["PIN_FAIL"]);
    component.onStagesChange([{ failure_threshold: 5, priority: 1, actions: [] }]);
    component.onPriorityInput("3");
    expect(component.priorityUnique()).toBe(false);
    expect(component.priorityConflict()?.name).toBe("Brute Force");
    expect(component.canSave()).toBe(false);
    // a free priority number clears the collision
    component.onPriorityInput("4");
    expect(component.priorityUnique()).toBe(true);
    expect(component.canSave()).toBe(true);
  });

  it("should not offer delete for a new (unsaved) policy", async () => {
    await component.deletePolicy();
    expect(policyServiceMock.deleteWithConfirmDialog).not.toHaveBeenCalled();
  });

  it("should prefill from a template and clear back to empty on clear template", () => {
    policyServiceMock.templates.set([
      {
        key: "password_bruteforce",
        description: "Lock a user after repeated wrong passwords.",
        // Without a "conditions" key, as the backend serves it: a template applies everywhere.
        policy: {
          name: "Password Brute-Force",
          time_window_seconds: 900,
          enabled: true,
          dry_run: false,
          // Templates carry no policy-level priority.
          priority: null,
          target: "user",
          count_mode: "PER_REQUEST",
          reset_on_success: true,
          counter_types_to_track: ["PASSWORD_FAIL"],
          stages: [{ failure_threshold: 10, priority: 1, actions: [{ action_type: "LOCK_USER", action_value: null }] }]
        }
      }
    ]);

    component.applyTemplate("password_bruteforce");
    expect(component.editPolicy().name).toBe("Password Brute-Force");
    expect(component.editPolicy().stages.length).toBe(1);
    // The admin must still pick a priority: the template leaves it empty.
    expect(component.editPolicy().priority).toBeNull();
    expect(component.editPolicy().conditions).toBeUndefined();
    expect(component.selectedTemplateKey()).toBe("password_bruteforce");

    // The clear button resets the prefill back to the empty policy.
    component.clearTemplateSelection();
    expect(component.editPolicy().name).toBe("");
    expect(component.editPolicy().stages).toEqual([]);
    expect(component.editPolicy().counter_types_to_track).toEqual([]);
    expect(component.selectedTemplateKey()).toBeNull();
  });

  describe("a template carrying an email action", () => {
    beforeEach(() => {
      policyServiceMock.templates.set([
        {
          key: "mfa_bruteforce",
          description: "Lock a user whose second factor keeps failing.",
          policy: {
            ...EMPTY_TEMPLATE_POLICY,
            name: "MFA Brute-Force",
            counter_types_to_track: ["MFA_FAIL"],
            stages: [
              {
                failure_threshold: 5,
                priority: 1,
                actions: [
                  { action_type: "LOCK_USER", action_value: 600 },
                  { action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "" } }
                ]
              }
            ]
          }
        }
      ]);
    });

    const applyAndReadActionTypes = (rights: string[]): LockoutActionType[] => {
      const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights });
      component.applyTemplate("mfa_bruteforce");
      return component.editPolicy().stages[0].actions.map((action) => action.action_type);
    };

    it("prefills it for an admin who may read the SMTP configuration", () => {
      expect(applyAndReadActionTypes(["smtpserver_read"])).toEqual(["LOCK_USER", "EMAIL_ADMIN"]);
    });

    // The email action stays offered without the right; the identifier field just becomes a free-text
    // input explaining why the configured servers cannot be listed.
    it("prefills it for one who may not, too", () => {
      expect(applyAndReadActionTypes([])).toEqual(["LOCK_USER", "EMAIL_ADMIN"]);
      expect(component.editPolicy().name).toBe("MFA Brute-Force");
    });
  });

  it("should expose the selected template's description as a hint", () => {
    policyServiceMock.templates.set([
      { key: "k", description: "Lock a user after repeated wrong passwords.", policy: EMPTY_TEMPLATE_POLICY }
    ]);
    expect(component.selectedTemplateDescription()).toBe("");
    component.applyTemplate("k");
    expect(component.selectedTemplateDescription()).toBe("Lock a user after repeated wrong passwords.");
  });

  it("should update the policy target on target change", () => {
    component.onTargetChange("source_ip");
    expect(component.editPolicy().target).toBe("source_ip");
  });

  describe("targetOptions", () => {
    it("should fall back to the fixed enum until /targets loads", () => {
      policyServiceMock.targets.set([]);
      expect(component.targetOptions()).toEqual(["user", "source_ip"]);
    });

    it("should use the backend targets once loaded", () => {
      policyServiceMock.targets.set(["user", "source_ip"]);
      expect(component.targetOptions()).toEqual(["user", "source_ip"]);
    });
  });

  describe("targetLabel", () => {
    it("should return the human label for a known target", () => {
      expect(component.targetLabel("user")).toBe("User");
      expect(component.targetLabel("source_ip")).toBe("Source IP");
    });

    it("should fall back to the raw value for an unknown target", () => {
      expect(component.targetLabel("realm")).toBe("realm");
    });
  });

  describe("targetActionsValid", () => {
    const stageWith = (actionType: LockoutActionType) => [
      { failure_threshold: 5, priority: 1, actions: [{ action_type: actionType, action_value: null }] }
    ];

    beforeEach(() => {
      policyServiceMock.actionsByTarget.set({
        user: ["LOCK_USER", "ALLOW", "DENY"],
        source_ip: ["BLOCK_IP", "ALLOW", "DENY"]
      });
    });

    it("should be valid when every stage action is allowed for the target", () => {
      component.onTargetChange("user");
      component.onStagesChange(stageWith("LOCK_USER"));
      expect(component.targetActionsValid()).toBe(true);
    });

    it("should be invalid when a stage action is not allowed for the target", () => {
      component.onTargetChange("source_ip");
      component.onStagesChange(stageWith("LOCK_USER"));
      expect(component.targetActionsValid()).toBe(false);
      expect(component.canSave()).toBe(false);
    });

    it("should not block while the allowed-actions list is still empty", () => {
      policyServiceMock.actionsByTarget.set({} as Record<LockoutTarget, LockoutActionType[]>);
      policyServiceMock.actionTypes.set([]);
      component.onTargetChange("source_ip");
      component.onStagesChange(stageWith("LOCK_USER"));
      expect(component.targetActionsValid()).toBe(true);
    });
  });

  describe("reset on success", () => {
    it("should update reset_on_success on change", () => {
      component.onResetOnSuccessChange(false);
      expect(component.editPolicy().reset_on_success).toBe(false);
      component.onResetOnSuccessChange(true);
      expect(component.editPolicy().reset_on_success).toBe(true);
    });

    // A source-IP policy aggregates across accounts, so the setting is inert there: the control stays
    // visible - so the target change explains itself - but cannot be operated.
    it("should not apply to a source-IP policy", () => {
      component.onTargetChange("source_ip");
      expect(component.resetOnSuccessApplies()).toBe(false);
      component.onTargetChange("user");
      expect(component.resetOnSuccessApplies()).toBe(true);
    });

    // The setting is inert for a source-IP policy, so it is cleared rather than left describing a reset that
    // never happens. It stays cleared on the way back, where the control is enabled again.
    it("should clear the checkbox when the target changes", () => {
      expect(component.editPolicy().reset_on_success).toBe(true);
      component.onTargetChange("source_ip");
      expect(component.editPolicy().reset_on_success).toBe(false);
      component.onTargetChange("user");
      expect(component.editPolicy().reset_on_success).toBe(false);
    });

    // A source-IP template must not prefill a ticked box the admin then cannot untick, which is what the
    // backend default would produce if it were applied regardless of target.
    it("should clear the checkbox when a source-IP template is applied", () => {
      policyServiceMock.templates.set([
        {
          key: "spray_key",
          description: "d",
          policy: { ...EMPTY_TEMPLATE_POLICY, target: "source_ip", count_mode: "DISTINCT_USERS" }
        }
      ]);
      component.applyTemplate("spray_key");
      expect(component.editPolicy().reset_on_success).toBe(false);
      expect(component.resetOnSuccessApplies()).toBe(false);
    });

    it("should render the checkbox disabled for a source-IP policy", () => {
      component.onTargetChange("source_ip");
      fixture.detectChanges();
      const checkbox: HTMLInputElement = fixture.nativeElement.querySelector(".ca-reset-on-success input");
      expect(checkbox.disabled).toBe(true);
    });

    // A template that carries no choice here falls back to the backend's default.
    it("should default a template prefill to resetting", () => {
      policyServiceMock.templates.set([
        {
          key: "no_reset_key",
          description: "d",
          policy: { ...EMPTY_TEMPLATE_POLICY, reset_on_success: undefined }
        }
      ]);
      component.applyTemplate("no_reset_key");
      expect(component.editPolicy().reset_on_success).toBe(true);
    });

    // A template that does carry one (the rate limits, which must not have their count cleared by a success) keeps it.
    it("should keep a template's explicit reset-on-success choice", () => {
      policyServiceMock.templates.set([
        {
          key: "rate_limit_key",
          description: "d",
          policy: { ...EMPTY_TEMPLATE_POLICY, reset_on_success: false }
        }
      ]);
      component.applyTemplate("rate_limit_key");
      expect(component.editPolicy().reset_on_success).toBe(false);
    });
  });

  describe("count mode", () => {
    beforeEach(() => {
      policyServiceMock.countModesByTarget.set({
        user: ["PER_ATTEMPT", "PER_REQUEST"],
        source_ip: ["DISTINCT_USERS", "PER_ATTEMPT", "PER_REQUEST"]
      });
    });

    it("should offer the current mode until /targets loads", () => {
      policyServiceMock.countModesByTarget.set({} as Record<LockoutTarget, CountMode[]>);
      expect(component.countModeOptions()).toEqual([component.editPolicy().count_mode]);
    });

    it("should offer the target's count modes once loaded", () => {
      component.onTargetChange("source_ip");
      expect(component.countModeOptions()).toEqual(["DISTINCT_USERS", "PER_ATTEMPT", "PER_REQUEST"]);
    });

    it("should update the count mode on change", () => {
      component.onCountModeChange("PER_ATTEMPT");
      expect(component.editPolicy().count_mode).toBe("PER_ATTEMPT");
    });

    it("should not change the count mode when the target changes", () => {
      component.onTargetChange("source_ip");
      component.onCountModeChange("DISTINCT_USERS");
      // Switching to a target where the mode is still valid leaves it untouched...
      component.onTargetChange("source_ip");
      expect(component.editPolicy().count_mode).toBe("DISTINCT_USERS");
      // ...and switching to one where it is invalid also leaves it untouched (surfaced as an error, not rewritten).
      component.onTargetChange("user");
      expect(component.editPolicy().count_mode).toBe("DISTINCT_USERS");
    });

    it("should be valid when the count mode is supported by the target", () => {
      component.onTargetChange("source_ip");
      component.onCountModeChange("PER_ATTEMPT");
      expect(component.countModeValid()).toBe(true);
    });

    it("should be invalid and block saving when the count mode is not supported by the target", () => {
      component.onTargetChange("source_ip");
      component.onCountModeChange("DISTINCT_USERS");
      component.onTargetChange("user");
      expect(component.countModeValid()).toBe(false);
      expect(component.canSave()).toBe(false);
    });

    it("should not block while the supported-modes list is still empty", () => {
      policyServiceMock.countModesByTarget.set({} as Record<LockoutTarget, CountMode[]>);
      component.onTargetChange("user");
      component.onCountModeChange("DISTINCT_USERS");
      expect(component.countModeValid()).toBe(true);
    });

    it("should label the count modes", () => {
      expect(component.countModeLabel("PER_REQUEST")).toBe("Per Request");
      expect(component.countModeLabel("DISTINCT_USERS")).toBe("Distinct Users");
      expect(component.countModeLabel("WHATEVER")).toBe("WHATEVER");
    });
  });
});
