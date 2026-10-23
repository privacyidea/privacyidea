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
import { MatSelect } from "@angular/material/select";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { By } from "@angular/platform-browser";
import { ActivatedRoute, convertToParamMap, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService } from "@services/auth/auth.service";
import { CA_ERR, toPolicyFormModel } from "@services/conditional-access/conditional-access-policy-form";
import {
  ConditionalAccessPolicyService,
  CountMode,
  ConditionalAccessActionType,
  ConditionalAccessPolicy,
  ConditionalAccessPolicySaveParams,
  ConditionalAccessPolicyStage,
  ConditionalAccessTarget
} from "@services/conditional-access/conditional-access-policy.service";
import { NotificationService } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { DialogService } from "@services/dialog/dialog.service";
import { SmtpService } from "@services/smtp/smtp.service";
import {
  MockAuthService,
  MockConditionalAccessPolicyService,
  MockNotificationService,
  MockPendingChangesService,
  MockRouter,
  MockSmtpService
} from "@testing/mock-services";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { BehaviorSubject } from "rxjs";
import { DurationUnit } from "@utils/duration-unit.utils";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";
import { AuthEventType } from "@services/conditional-access/conditional-access-policy.service";
import { ConditionalAccessEditPageComponent } from "./conditional-access-edit-page.component";

globalThis.IntersectionObserver = class IntersectionObserver {
  disconnect = jest.fn();
  observe = jest.fn();
  unobserve = jest.fn();
  takeRecords = (): IntersectionObserverEntry[] => [];
} as unknown as typeof IntersectionObserver;

const mockPolicy: ConditionalAccessPolicy = {
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
  stages: [{ failure_threshold: 5, actions: [{ action_type: "LOCK_USER", action_value: 600 }] }],
  conditions: []
};

const EMPTY_TEMPLATE_POLICY: ConditionalAccessPolicySaveParams = {
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
  stages: [{ failure_threshold: 10, actions: [{ action_type: "LOCK_USER", action_value: 600 }] }]
};

// Writes into the form model in the shape of the stored policy, as loaded data and the stage and condition editors do.
const patchPolicy = (
  component: ConditionalAccessEditPageComponent,
  partial: Partial<ConditionalAccessPolicySaveParams>
): void => component["policyModel"].set(toPolicyFormModel({ ...component.editPolicy(), ...partial }));

// Replaces the stages of the form, as the stage editor does.
const setStages = (component: ConditionalAccessEditPageComponent, stages: ConditionalAccessPolicyStage[]): void =>
  patchPolicy(component, { stages });

const errorKinds = (field: () => { errors(): { kind: string }[] }): string[] =>
  field()
    .errors()
    .map((error) => error.kind);

// The input of the mat-form-field with the given label.
const inputOf = (fixture: ComponentFixture<unknown>, label: string): HTMLInputElement =>
  Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll("mat-form-field"))
    .find((field) => field.querySelector("mat-label")?.textContent?.trim() === label)!
    .querySelector("input")!;

// Types into a field like a user does; the blur that follows touches it, which is what lets its mat-error render.
const typeInto = (fixture: ComponentFixture<unknown>, label: string, value: string, blur = true): void => {
  const input = inputOf(fixture, label);
  input.value = value;
  input.dispatchEvent(new Event("input"));
  if (blur) {
    input.dispatchEvent(new Event("blur"));
  }
  fixture.detectChanges();
};

// Picks the option at `index` of the select of the mat-form-field with the given label, through the opened panel.
const pickOption = async (fixture: ComponentFixture<unknown>, label: string, index: number): Promise<void> => {
  const field = fixture.debugElement
    .queryAll(By.css("mat-form-field"))
    .find((debugElement) => debugElement.nativeElement.querySelector("mat-label")?.textContent?.trim() === label)!;
  const select = field.query(By.directive(MatSelect)).componentInstance as MatSelect;
  select.open();
  fixture.detectChanges();
  await fixture.whenStable();
  (select.panel.nativeElement.querySelectorAll("mat-option")[index] as HTMLElement).click();
  fixture.detectChanges();
  await fixture.whenStable();
};

afterEach(() => document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = "")));

// jsdom has no validity.badInput; a number input that holds text the browser cannot parse is simulated.
const rejectInputAsNumber = (input: HTMLInputElement): void => {
  Object.defineProperty(input, "validity", { configurable: true, get: () => ({ badInput: true }) });
};

// Writes into the bound form fields, which is what a control does on input. Each setter flushes change detection so
// the effects that react to the form (clearing reset-on-success for a source-IP target) have run on return.
const fieldHelpers = (
  component: ConditionalAccessEditPageComponent,
  fixture: ComponentFixture<ConditionalAccessEditPageComponent>
) => ({
  setTarget: (target: ConditionalAccessTarget) => {
    component.policyForm.target().value.set(target);
    fixture.detectChanges();
  },
  setCountMode: (countMode: CountMode) => component.policyForm.count_mode().value.set(countMode),
  setCounterTypes: (types: AuthEventType[]) => component.policyForm.counter_types_to_track().value.set(types),
  setPriority: (priority: string) => component.policyForm.priority().value.set(priority),
  setResetOnSuccess: (checked: boolean) => component.policyForm.reset_on_success().value.set(checked),
  setTimeWindow: (value: string, unit?: DurationUnit) => {
    component.policyForm.time_window_value().value.set(value);
    if (unit) {
      component.policyForm.time_window_unit().value.set(unit);
    }
  }
});

describe("ConditionalAccessEditPageComponent — edit mode", () => {
  let helpers: ReturnType<typeof fieldHelpers>;
  let component: ConditionalAccessEditPageComponent;
  let fixture: ComponentFixture<ConditionalAccessEditPageComponent>;
  let policyServiceMock: MockConditionalAccessPolicyService;
  let pendingChangesServiceMock: MockPendingChangesService;
  let routerMock: MockRouter;
  let dialogServiceMock: MockDialogService;
  let notificationServiceMock: MockNotificationService;
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
        { provide: DialogService, useClass: MockDialogService },
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
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    policyServiceMock.policies.set([mockPolicy]);

    fixture = TestBed.createComponent(ConditionalAccessEditPageComponent);
    component = fixture.componentInstance;
    helpers = fieldHelpers(component, fixture);
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
    patchPolicy(component, { time_window_seconds: 900 });
    expect(component.hasChanges()).toBe(true);
  });

  it("should become invalid when the name is cleared", () => {
    patchPolicy(component, { name: "" });
    expect(component.canSave()).toBe(false);
  });

  it("should become invalid when counter_types_to_track is emptied", () => {
    helpers.setCounterTypes([]);
    expect(hasError(component.policyForm.counter_types_to_track, ERR.required)).toBe(true);
    expect(component.canSave()).toBe(false);
  });

  it("should flag the tracked event types as an error while none are selected", () => {
    helpers.setCounterTypes([]);
    expect(component.saveBlockers()).toContain("At least one tracked event type is required.");

    helpers.setCounterTypes(["PIN_FAIL"]);
    expect(component.saveBlockers()).not.toContain("At least one tracked event type is required.");
  });

  it("should render the tracked event types error once the select is touched", () => {
    helpers.setCounterTypes([]);
    fixture.detectChanges();
    expect(renderedErrors()).not.toContain(
      "At least one event type is required. A policy that counts nothing never trips."
    );

    component.policyForm.counter_types_to_track().markAsTouched();
    fixture.detectChanges();
    expect(renderedErrors()).toContain(
      "At least one event type is required. A policy that counts nothing never trips."
    );
  });

  it("should list nothing to fix while the policy is valid", () => {
    expect(component.canSave()).toBe(true);
    expect(component.saveBlockers()).toEqual([]);
  });

  // The message waits for the field to be touched, and clears once the name is valid again.
  it("should only show the name error once the field has been touched", () => {
    typeInto(fixture, "Name", "", false);
    expect(renderedErrors()).not.toContain("Name is required.");
    inputOf(fixture, "Name").dispatchEvent(new Event("blur"));
    fixture.detectChanges();
    expect(renderedErrors()).toContain("Name is required.");
    typeInto(fixture, "Name", "Valid again");
    expect(renderedErrors()).not.toContain("Name is required.");
  });

  it("should count a blank name as a missing one", () => {
    typeInto(fixture, "Name", "   ");
    expect(errorKinds(component.policyForm.name)).toEqual([ERR.required]);
    expect(renderedErrors()).toContain("Name is required.");
    expect(component.canSave()).toBe(false);
  });

  it("should write the typed name to the model and show its length", () => {
    typeInto(fixture, "Name", "Typed");
    expect(component.editPolicy().name).toBe("Typed");
    expect(fixture.nativeElement.textContent).toContain("5 / 255");
  });

  it("should keep the loaded form when the routed id names no known policy", () => {
    // The list may not hold the id yet (a deep link before /policy has answered), so the editor
    // leaves the form as it stands rather than blanking it; the effect below reloads it once the
    // matching policy does arrive.
    paramMap$.next(convertToParamMap({ id: "4711" }));
    expect(component.isNewPolicy()).toBe(false);
    expect(component.editPolicy().name).toBe(mockPolicy.name);

    // A list that still lacks that id changes nothing either.
    policyServiceMock.policies.set([{ ...mockPolicy, id: 99, name: "Someone else" }]);
    fixture.detectChanges();
    expect(component.editPolicy().name).toBe(mockPolicy.name);

    // When it does arrive, the form picks it up.
    policyServiceMock.policies.set([{ ...mockPolicy, id: 4711, name: "Arrived late" }]);
    fixture.detectChanges();
    expect(component.editPolicy().name).toBe("Arrived late");
  });

  // A stored window is displayed in the coarsest unit that divides it evenly, so 3600s reads as
  // "1 hours" rather than "3600 seconds".
  it.each([
    [3600, "hours", 1],
    [600, "minutes", 10],
    [90, "seconds", 90]
  ])("should show a window of %ss in the coarsest fitting unit", (seconds, unit, value) => {
    policyServiceMock.templates.set([
      {
        key: "window",
        description: "",
        policy: { ...EMPTY_TEMPLATE_POLICY, time_window_seconds: seconds }
      }
    ]);
    component.applyTemplate("window");
    expect(component.policyForm.time_window_unit().value()).toBe(unit);
    expect(component.policyForm.time_window_value().value()).toBe(String(value));
  });

  it("should report no priority conflict while the priority is empty", () => {
    // An empty priority cannot collide with anything, so it is reported as "required", not as a clash.
    policyServiceMock.policies.set([mockPolicy, { ...mockPolicy, id: 99, name: "Other", priority: 4 }]);
    helpers.setPriority("");
    expect(component.priorityConflict()).toBeUndefined();
    expect(hasError(component.policyForm.priority, CA_ERR.priorityTaken)).toBe(false);
    expect(errorKinds(component.policyForm.priority)).toEqual([ERR.required]);
  });

  it("should show the count mode error right after a target pick that invalidates the mode", async () => {
    policyServiceMock.countModesByTarget.set({ user: ["PER_REQUEST"], source_ip: ["DISTINCT_USERS"] });
    fixture.detectChanges();
    expect(component.policyForm.count_mode().touched()).toBe(false);
    await pickOption(fixture, "Target", 1);
    fixture.detectChanges();
    expect(errorKinds(component.policyForm.count_mode)).toEqual([CA_ERR.countModeNotAllowed]);
    expect(fixture.nativeElement.textContent).toContain("This count mode is not allowed for the selected target.");
  });

  describe("copy", () => {
    const copyButton = (): HTMLButtonElement | undefined =>
      Array.from<HTMLButtonElement>(fixture.nativeElement.querySelectorAll(".action-buttons button")).find((button) =>
        button.textContent?.includes("Copy")
      );
    const setRights = (rights: string[]) => {
      const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights });
      fixture.detectChanges();
    };
    const navigatedDraft = (): ConditionalAccessPolicySaveParams =>
      routerMock.navigateByUrl.mock.calls.at(-1)![1].state.copyOf;

    it("should offer the copy next to the save for an admin who may write policies", () => {
      setRights(["conditional_access_policy_write"]);
      expect(copyButton()).toBeDefined();
    });

    it("should not offer the copy without the right to write policies", () => {
      setRights([]);
      expect(copyButton()).toBeUndefined();
    });

    it("should open the create page with the policy as the draft", () => {
      component.copyPolicy();

      expect(routerMock.navigateByUrl).toHaveBeenCalledWith(
        ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_NEW,
        expect.objectContaining({ state: { copyOf: expect.objectContaining({ name: "Brute Force" }) } })
      );
      expect(pendingChangesServiceMock.clearAllRegistrations).toHaveBeenCalled();
    });

    it("should leave the id, the priority and the enforcement date out of the draft", () => {
      patchPolicy(component, { enforced_since: "2026-01-01T00:00:00" });
      component.copyPolicy();

      const draft = navigatedDraft();
      expect(draft).not.toHaveProperty("id");
      expect(draft.priority).toBeNull();
      expect(draft.enforced_since).toBeNull();
    });

    it("should carry the unsaved edits of the editor into the draft and leave the stored policy alone", () => {
      patchPolicy(component, { name: "Renamed", time_window_seconds: 1200 });
      component.copyPolicy();

      expect(navigatedDraft()).toEqual(expect.objectContaining({ name: "Renamed", time_window_seconds: 1200 }));
      expect(navigatedDraft().stages).toEqual(mockPolicy.stages);
      expect(component.policy().name).toBe("Brute Force");
      expect(component.editPolicy().priority).toBe(1);
    });

    it("should not hand the draft the objects of the editor", () => {
      component.copyPolicy();
      navigatedDraft().stages[0].failure_threshold = 99;
      expect(component.editPolicy().stages[0].failure_threshold).toBe(5);
    });

    it("should disable the copy while the policy is being saved", async () => {
      setRights(["conditional_access_policy_write"]);
      let finish!: (id: number | undefined) => void;
      policyServiceMock.savePolicy.mockReturnValueOnce(
        new Promise<number | undefined>((resolve) => (finish = resolve))
      );

      const saving = component.savePolicy();
      fixture.detectChanges();
      expect(copyButton()!.disabled).toBe(true);

      finish(undefined);
      await saving;
      fixture.detectChanges();
      expect(copyButton()!.disabled).toBe(false);
    });
  });

  describe("name conflict", () => {
    const rename = (name: string) => patchPolicy(component, { name });

    beforeEach(() => {
      policyServiceMock.policies.set([mockPolicy, { ...mockPolicy, id: 99, name: "Other", priority: 4 }]);
    });

    it("should not count the policy being edited as a conflict with itself", () => {
      expect(component.nameConflict()).toBeUndefined();
      expect(component.canSave()).toBe(true);
    });

    it("should name the policy that already carries the new name and block saving", () => {
      rename("Other");
      expect(component.nameConflict()?.id).toBe(99);
      expect(component.canSave()).toBe(false);
      expect(component.saveBlockers()).toEqual(["A policy with this name already exists."]);
    });

    it("should ignore the case and surrounding spaces, as the backend and MySQL and MariaDB do", () => {
      rename("OTHER ");
      expect(component.nameConflict()?.id).toBe(99);
      expect(component.canSave()).toBe(false);

      rename(" other");
      expect(component.nameConflict()?.id).toBe(99);
      expect(component.canSave()).toBe(false);
    });

    it("should not save a name that the list has revealed as taken, and say why", async () => {
      rename("Other");
      policyServiceMock.savePolicy.mockClear();

      expect(await component.savePolicy()).toBe(false);

      expect(policyServiceMock.savePolicy).not.toHaveBeenCalled();
      expect(notificationServiceMock.error).toHaveBeenCalledWith("A policy with this name already exists.");
    });

    it("should not report the name of a new policy as taken once the list holds it while the save runs", async () => {
      component.isNewPolicy.set(true);
      rename("Fresh");
      let conflictDuringSave: ConditionalAccessPolicy | undefined;
      policyServiceMock.savePolicy.mockImplementationOnce(async () => {
        policyServiceMock.policies.set([...policyServiceMock.policies(), { ...mockPolicy, id: 100, name: "Fresh" }]);
        conflictDuringSave = component.nameConflict();
        return 100;
      });

      await component.savePolicy();

      expect(conflictDuringSave).toBeUndefined();
      expect(component.nameConflict()).toBeUndefined();
    });

    it("should report the name again when the save fails and another policy took it", async () => {
      rename("Fresh");
      policyServiceMock.savePolicy.mockResolvedValueOnce(undefined);
      await component.savePolicy();
      policyServiceMock.policies.set([...policyServiceMock.policies(), { ...mockPolicy, id: 100, name: "Fresh" }]);

      expect(component.nameConflict()?.id).toBe(100);
    });

    it("should allow a change of the case of the own name", () => {
      rename("brute force");
      expect(component.nameConflict()).toBeUndefined();
      expect(component.canSave()).toBe(true);
    });

    it("should allow saving again once the name is free", () => {
      rename("Other");
      rename("Other 2");
      expect(component.nameConflict()).toBeUndefined();
      expect(component.canSave()).toBe(true);
    });

    it("should never report the unchanged name, even when a case twin of it exists", () => {
      policyServiceMock.policies.set([mockPolicy, { ...mockPolicy, id: 99, name: "brute force", priority: 4 }]);
      expect(component.nameConflict()).toBeUndefined();
      expect(component.canSave()).toBe(true);
    });

    it("should show the error message at once, without the name field having been left", () => {
      rename("Other");
      fixture.detectChanges();

      expect(component.policyForm.name().touched()).toBe(true);
      expect(fixture.nativeElement.textContent).toContain('A policy named "Other" already exists.');
    });

    it("should not show the error message for a free name", () => {
      rename("Another name");
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).not.toContain("already exists");
    });
  });

  it("should name a name that is too long", () => {
    patchPolicy(component, { name: "n".repeat(256) });
    expect(hasError(component.policyForm.name, ERR.maxLength)).toBe(true);
    expect(component.saveBlockers()).toEqual(["Name must not exceed 255 characters."]);
  });

  it("should count the length of the name without the spaces around it", () => {
    patchPolicy(component, { name: `  ${"n".repeat(255)}  ` });
    expect(hasError(component.policyForm.name, ERR.maxLength)).toBe(false);
    expect(component.canSave()).toBe(true);
  });

  it("should render the name length error once the name is touched", () => {
    typeInto(fixture, "Name", "n".repeat(256));
    expect(renderedErrors()).toContain("Name must not exceed 255 characters.");
  });

  it("should name a time window below one second", () => {
    helpers.setTimeWindow("0");
    expect(component.saveBlockers()).toEqual(["Time window must be a whole number of at least 1 second."]);
  });

  it("should name a priority already held by another policy", () => {
    policyServiceMock.policies.set([mockPolicy, { ...mockPolicy, id: 99, name: "Other", priority: 4 }]);
    helpers.setPriority("4");
    expect(component.saveBlockers()).toEqual(["Priority must be unique across policies."]);
  });

  it("should name duplicate stage thresholds", () => {
    setStages(component, [
      { failure_threshold: 5, actions: [{ action_type: "LOCK_USER", action_value: 60 }] },
      { failure_threshold: 5, actions: [{ action_type: "LOCK_USER", action_value: 60 }] }
    ]);
    expect(component.saveBlockers()).toEqual(["Each stage must have a different failure threshold."]);
  });

  it("should name a stage action with an invalid value", () => {
    setStages(component, [{ failure_threshold: 5, actions: [{ action_type: "LOCK_USER", action_value: -1 }] }]);
    expect(component.saveBlockers()).toContain("Fix the highlighted action value before saving.");
    expect(component.canSave()).toBe(false);
  });

  it("should name an action that the target does not allow", () => {
    policyServiceMock.actionsByTarget.set({
      user: ["LOCK_USER", "DENY"],
      source_ip: ["BLOCK_IP", "DENY"]
    });
    helpers.setTarget("source_ip");
    setStages(component, [{ failure_threshold: 5, actions: [{ action_type: "LOCK_USER", action_value: null }] }]);
    expect(component.saveBlockers()).toContain("Some actions are not allowed for the selected target.");
  });

  it("should name a count mode that the target does not support", () => {
    policyServiceMock.countModesByTarget.set({
      user: ["PER_ATTEMPT", "PER_REQUEST"],
      source_ip: ["DISTINCT_USERS", "PER_ATTEMPT", "PER_REQUEST"]
    });
    helpers.setTarget("source_ip");
    helpers.setCountMode("DISTINCT_USERS");
    helpers.setTarget("user");
    expect(component.saveBlockers()).toContain("The selected count mode is not allowed for the selected target.");
  });

  it("should name every reason saving is blocked", () => {
    patchPolicy(component, {
      name: "",
      priority: null,
      counter_types_to_track: [],
      stages: [{ failure_threshold: 0, actions: [] }]
    });
    expect(component.canSave()).toBe(false);
    expect(component.saveBlockers()).toEqual([
      "Name is required.",
      "Priority is required.",
      "At least one tracked event type is required.",
      "Every stage needs a failure threshold of at least 1 - or 0 on a stage carrying only DENY."
    ]);
  });

  it("should become invalid when stages is emptied", () => {
    setStages(component, []);
    expect(component.stagesValid()).toBe(false);
    expect(component.canSave()).toBe(false);
  });

  it("should stay valid when a zero-threshold stage only carries DENY", () => {
    setStages(component, [{ failure_threshold: 0, actions: [{ action_type: "DENY", action_value: null }] }]);
    expect(component.stagesValid()).toBe(true);
  });

  // A threshold counts failures, so only a standing DENY verdict may sit at 0; the backend
  // refuses the rest in _validate_threshold_for_actions.
  it.each([
    ["no action to justify it", []],
    ["an action that reacts to a count", [{ action_type: "LOCK_USER", action_value: 60 }]],
    [
      "a standing verdict mixed with a counting action",
      [
        { action_type: "DENY", action_value: null },
        { action_type: "LOCK_USER", action_value: 60 }
      ]
    ]
  ])("should become invalid when a zero-threshold stage has %s", (_label, actions) => {
    setStages(component, [{ failure_threshold: 0, actions: actions as never }]);
    expect(component.stagesValid()).toBe(false);
    expect(component.canSave()).toBe(false);
  });

  it("should become invalid when a stage has a negative threshold", () => {
    setStages(component, [{ failure_threshold: -1, actions: [] }]);
    expect(component.stagesValid()).toBe(false);
  });

  it("should block saving when two stages share a failure threshold", () => {
    setStages(component, [
      { failure_threshold: 5, actions: [] },
      { failure_threshold: 5, actions: [] }
    ]);
    expect(component.stageThresholdsUnique()).toBe(false);
    expect(component.canSave()).toBe(false);
    // distinct thresholds are fine
    setStages(component, [
      { failure_threshold: 5, actions: [] },
      { failure_threshold: 10, actions: [] }
    ]);
    expect(component.stageThresholdsUnique()).toBe(true);
  });

  it("should convert the entered value to seconds using the selected unit", () => {
    helpers.setTimeWindow("120", "seconds");
    expect(component.editPolicy().time_window_seconds).toBe(120);
    helpers.setTimeWindow("10", "minutes");
    expect(component.editPolicy().time_window_seconds).toBe(600);
    component.policyForm.time_window_unit().value.set("hours");
    expect(component.editPolicy().time_window_seconds).toBe(36000);
  });

  it("should write the typed window and the picked unit through the controls", () => {
    typeInto(fixture, "Time window", "3");
    expect(component.policyForm.time_window_value().dirty()).toBe(true);
    // The stored 10 minutes show in minutes, so the typed 3 is 3 minutes.
    expect(component.editPolicy().time_window_seconds).toBe(180);
    expect(component.hasChanges()).toBe(true);
  });

  it.each([
    ["0", ERR.min],
    ["-5", ERR.min],
    ["1.5", CA_ERR.notInteger],
    ["", ERR.required],
    ["   ", ERR.required]
  ])("should reject the time window %j with %s and send no window", (text, kind) => {
    helpers.setTimeWindow(text);
    expect(errorKinds(component.policyForm.time_window_value)).toEqual([kind]);
    expect(component.canSave()).toBe(false);
    expect(component.editPolicy().time_window_seconds).toBeLessThanOrEqual(0);
  });

  it("should render the time window messages once the field is touched", () => {
    typeInto(fixture, "Time window", "0");
    expect(renderedErrors()).toContain("Time window must be at least 1.");
    typeInto(fixture, "Time window", "1.5");
    expect(renderedErrors()).toContain("Enter a whole number.");
    typeInto(fixture, "Time window", "");
    expect(renderedErrors()).toContain("Time window is required.");
    typeInto(fixture, "Time window", "2");
    expect(renderedErrors()).toEqual([]);
  });

  it("should report a time window the browser cannot parse as a number", () => {
    rejectInputAsNumber(inputOf(fixture, "Time window"));
    typeInto(fixture, "Time window", "");
    expect(hasError(component.policyForm.time_window_value, ERR.parse)).toBe(true);
    expect(component.canSave()).toBe(false);
    expect(renderedErrors()).toContain("Enter a valid number.");
  });

  it("should map priority text to a number, and to null for empty, non-numeric or decimal text", () => {
    helpers.setPriority("5");
    expect(component.editPolicy().priority).toBe(5);
    helpers.setPriority("abc");
    expect(component.editPolicy().priority).toBeNull();
    helpers.setPriority("");
    expect(component.editPolicy().priority).toBeNull();
    // A decimal must not be silently truncated to a passing integer.
    helpers.setPriority("1.5");
    expect(component.editPolicy().priority).toBeNull();
  });

  it("should keep the typed text so an invalid priority is explained, not wiped", () => {
    helpers.setPriority("1.5");
    expect(component.policyForm.priority().value()).toBe("1.5");
    expect(errorKinds(component.policyForm.priority)).toEqual([CA_ERR.notInteger]);
    helpers.setPriority("abc");
    expect(component.policyForm.priority().value()).toBe("abc");
    expect(errorKinds(component.policyForm.priority)).toEqual([CA_ERR.notInteger]);
    // 0 and negatives are out of range, not malformed; they are reported as a range error.
    helpers.setPriority("0");
    expect(errorKinds(component.policyForm.priority)).toEqual([ERR.min]);
    helpers.setPriority("2");
    expect(component.policyForm.priority().errors()).toEqual([]);
  });

  it("should distinguish an empty priority from an invalid one", () => {
    helpers.setPriority("");
    expect(errorKinds(component.policyForm.priority)).toEqual([ERR.required]);
    helpers.setPriority("   ");
    expect(errorKinds(component.policyForm.priority)).toEqual([ERR.required]);
  });

  it("should show the existing priority in the field in edit mode", () => {
    expect(component.policyForm.priority().value()).toBe(String(mockPolicy.priority));
    expect(inputOf(fixture, "Priority").value).toBe(String(mockPolicy.priority));
  });

  // mat-form-field only projects <mat-error> while its control is in an error state, so asserting on the field errors
  // alone would pass with nothing rendered; these helpers read the DOM instead.
  const renderedErrors = (): string[] =>
    Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map((element) =>
      (element as HTMLElement).textContent!.trim()
    );

  it("should render the priority error message in the DOM, not just compute it", () => {
    typeInto(fixture, "Priority", "1.5");
    expect(errorKinds(component.policyForm.priority)).toEqual([CA_ERR.notInteger]);
    expect(renderedErrors()).toContain("Enter a whole number.");
  });

  it("should render the priority range message for a priority below 1", () => {
    typeInto(fixture, "Priority", "0");
    expect(renderedErrors()).toContain("Priority must be at least 1.");
  });

  it("should render the priority message for text the browser cannot parse as a number", () => {
    rejectInputAsNumber(inputOf(fixture, "Priority"));
    typeInto(fixture, "Priority", "");
    expect(errorKinds(component.policyForm.priority)).toEqual([ERR.parse]);
    expect(component.canSave()).toBe(false);
    expect(renderedErrors()).toContain("Enter a valid number.");
    expect(renderedErrors()).not.toContain("Priority is required.");
  });

  it("should render the required-priority message when the field is cleared", () => {
    typeInto(fixture, "Priority", "");
    expect(renderedErrors()).toContain("Priority is required.");
  });

  it("should render the collision message naming the conflicting policy", () => {
    policyServiceMock.policies.set([mockPolicy, { ...mockPolicy, id: 99, name: "Other", priority: 4 }]);
    typeInto(fixture, "Priority", "4");
    expect(hasError(component.policyForm.priority, CA_ERR.priorityTaken)).toBe(true);
    expect(renderedErrors().join(" ")).toContain('Priority 4 is already used by "Other".');
  });

  it("should render no priority error for a valid, free priority", () => {
    typeInto(fixture, "Priority", "42");
    expect(component.editPolicy().priority).toBe(42);
    expect(renderedErrors()).toEqual([]);
  });

  // The dialog asks what to do with a trial's events, so it is the stored policy that decides
  // whether it appears at all - put the component in the state of one saved in dry run.
  const storedPolicyInDryRun = () => {
    component.policy.set({ ...component.policy(), dry_run: true });
    patchPolicy(component, { dry_run: true });
  };

  it("should toggle dry_run without calling the enable/disable endpoints", () => {
    component.toggleDryRun(true);
    expect(component.editPolicy().dry_run).toBe(true);
    expect(policyServiceMock.enablePolicy).not.toHaveBeenCalled();
    expect(policyServiceMock.disablePolicy).not.toHaveBeenCalled();
  });

  it("should ask via a dialog before turning dry_run off, and reset counters by default", async () => {
    storedPolicyInDryRun();
    dialogServiceMock.openDialogAsync = jest.fn().mockResolvedValue({ resetCounters: true });

    await component.toggleDryRun(false);

    expect(dialogServiceMock.openDialogAsync).toHaveBeenCalled();
    expect(component.editPolicy().dry_run).toBe(false);
    expect(component.editPolicy().reset_counters_on_enforce).toBe(true);
  });

  it("should keep the trial's counters when the dialog says so", async () => {
    storedPolicyInDryRun();
    dialogServiceMock.openDialogAsync = jest.fn().mockResolvedValue({ resetCounters: false });

    await component.toggleDryRun(false);

    expect(component.editPolicy().dry_run).toBe(false);
    expect(component.editPolicy().reset_counters_on_enforce).toBe(false);
  });

  it("should leave dry_run on when the dialog is cancelled", async () => {
    storedPolicyInDryRun();
    dialogServiceMock.openDialogAsync = jest.fn().mockResolvedValue(undefined);

    await component.toggleDryRun(false);

    expect(component.editPolicy().dry_run).toBe(true);
  });

  // The control flips itself on the change and [checked] reads an unchanged value, so nothing puts
  // it back: without this the page would show "dry run off" for a policy still in dry run.
  it("should put the toggle back when the dialog is cancelled", async () => {
    storedPolicyInDryRun();
    dialogServiceMock.openDialogAsync = jest.fn().mockResolvedValue(undefined);
    const toggle = { checked: false } as MatSlideToggle;

    await component.toggleDryRun(false, toggle);

    expect(toggle.checked).toBe(true);
  });

  // Switching a stored enforcing policy to dry run and back, without saving in between, changes
  // nothing and accumulates no trial - there is nothing to ask about.
  it("should not ask when the stored policy is not in dry run", async () => {
    dialogServiceMock.openDialogAsync = jest.fn();
    component.toggleDryRun(true);

    await component.toggleDryRun(false);

    expect(dialogServiceMock.openDialogAsync).not.toHaveBeenCalled();
    expect(component.editPolicy().dry_run).toBe(false);
    expect(component.editPolicy().reset_counters_on_enforce).toBeUndefined();
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
    setStages(component, [
      { failure_threshold: 5, actions: [] },
      { failure_threshold: 10, actions: [] }
    ]);
    await component.savePolicy();
    const payload = policyServiceMock.savePolicy.mock.calls.at(-1)![0];
    // toMatchObject rather than toEqual: Signal Forms stamps its own identity symbols onto the objects of the model it
    // wraps, which an exact comparison would trip over.
    expect(payload.stages).toMatchObject([
      { failure_threshold: 5, actions: [] },
      { failure_threshold: 10, actions: [] }
    ]);
  });

  describe("stages editor", () => {
    const stageItems = () =>
      Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll("app-conditional-access-stage-item"));
    const thresholdOf = (item: HTMLElement) => item.querySelector("input[type=number]") as HTMLInputElement;
    const typeInStage = (input: HTMLInputElement | HTMLTextAreaElement, value: string) => {
      input.value = value;
      input.dispatchEvent(new Event("input"));
      input.dispatchEvent(new Event("blur"));
      fixture.detectChanges();
    };
    const withStages = (stages: ConditionalAccessPolicyStage[]) => {
      setStages(component, stages);
      fixture.detectChanges();
    };
    const lock = { action_type: "LOCK_USER" as const, action_value: 60 };
    const stageNotes = () =>
      Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll(".ca-stages-error")).map((note) =>
        note.textContent?.trim()
      );

    it("should render one item per stage and see no change in them after loading", () => {
      expect(stageItems()).toHaveLength(1);
      expect(thresholdOf(stageItems()[0]).value).toBe("5");
      expect(component.hasChanges()).toBe(false);
    });

    it("should load the id, the name and the message of a stored stage without a change", () => {
      const stored: ConditionalAccessPolicy = {
        ...mockPolicy,
        stages: [{ id: 3, name: "Warn", error_message: "Locked.", failure_threshold: 5, actions: [lock] }]
      };
      policyServiceMock.policies.set([stored]);
      fixture.detectChanges();
      expect(component.hasChanges()).toBe(false);
      expect(component.editPolicy().stages).toMatchObject(stored.stages);
    });

    it("should write a typed threshold to the policy", () => {
      typeInStage(thresholdOf(stageItems()[0]), "7");
      expect(component.editPolicy().stages[0].failure_threshold).toBe(7);
      expect(component.hasChanges()).toBe(true);
      expect(component.canSave()).toBe(true);
    });

    it("should block saving and say why while the threshold is empty", () => {
      typeInStage(thresholdOf(stageItems()[0]), "");
      expect(component.canSave()).toBe(false);
      expect(component.stagesValid()).toBe(false);
      expect(component.saveBlockers()).toEqual(["Failure threshold is required."]);
      expect(stageNotes()).toContain(
        "At least one stage is required, and every stage needs a non-negative failure threshold."
      );
      expect(fixture.nativeElement.querySelector("app-conditional-access-stage-item mat-error")).toBeTruthy();
    });

    it("should not call stages without a threshold yet duplicates of each other", () => {
      withStages([
        { failure_threshold: 5, actions: [] },
        { failure_threshold: 10, actions: [] }
      ]);
      typeInStage(thresholdOf(stageItems()[0]), "");
      typeInStage(thresholdOf(stageItems()[1]), "");
      expect(component.stageThresholdsUnique()).toBe(true);
      expect(component.stagesValid()).toBe(false);
    });

    it("should show the reason at once when an added action no longer allows a threshold of 0", () => {
      withStages([{ failure_threshold: 0, actions: [{ action_type: "DENY", action_value: null }] }]);
      expect(component.stagesValid()).toBe(true);
      component.policyForm.stages[0].actions().value.update((actions) => [...actions, lock]);
      fixture.detectChanges();
      expect(component.stagesValid()).toBe(false);
      expect(fixture.nativeElement.querySelector("app-conditional-access-stage-item mat-error").textContent).toContain(
        "A threshold of 0 means"
      );
    });

    it("should send the stripped name of a stage and leave out a blank one", () => {
      typeInStage(fixture.nativeElement.querySelector(".ca-stage-name-field input"), "  Warn  ");
      expect(component.editPolicy().stages[0].name).toBe("Warn");
      expect(component.hasChanges()).toBe(true);
      typeInStage(fixture.nativeElement.querySelector(".ca-stage-name-field input"), "   ");
      expect(component.editPolicy().stages[0]).not.toHaveProperty("name");
      expect(component.hasChanges()).toBe(false);
    });

    it("should send the error message of a stage that has it switched on", async () => {
      policyServiceMock.savePolicy.mockResolvedValueOnce(1);
      (
        fixture.nativeElement.querySelector(".ca-stage-error-message-toggle mat-checkbox input") as HTMLInputElement
      ).click();
      fixture.detectChanges();
      typeInStage(fixture.nativeElement.querySelector(".ca-stage-error-message textarea"), "Locked out.");
      await component.savePolicy();
      expect(policyServiceMock.savePolicy.mock.calls.at(-1)![0].stages[0].error_message).toBe("Locked out.");
    });

    it("should add a stage from the button and send it", async () => {
      policyServiceMock.savePolicy.mockResolvedValueOnce(1);
      (fixture.nativeElement.querySelector(".ca-stages-list > .ca-add-button-row button") as HTMLButtonElement).click();
      fixture.detectChanges();
      expect(stageItems()).toHaveLength(2);
      expect(component.hasChanges()).toBe(true);
      expect(component.canSave()).toBe(true);
      await component.savePolicy();
      expect(policyServiceMock.savePolicy.mock.calls.at(-1)![0].stages).toMatchObject([
        { failure_threshold: 5 },
        { failure_threshold: 1, actions: [] }
      ]);
    });

    it("should remove a stage from its button and keep the item of the other", () => {
      withStages([
        { failure_threshold: 5, actions: [] },
        { failure_threshold: 10, actions: [] }
      ]);
      const [, second] = stageItems();
      (stageItems()[0].querySelector("button[aria-label='Remove stage']") as HTMLButtonElement).click();
      fixture.detectChanges();
      expect(stageItems()).toEqual([second]);
      expect(component.editPolicy().stages).toMatchObject([{ failure_threshold: 10 }]);
      expect(component.stagesValid()).toBe(true);
    });

    it("should name the stage that is left after removing the only one as missing", () => {
      (stageItems()[0].querySelector("button[aria-label='Remove stage']") as HTMLButtonElement).click();
      fixture.detectChanges();
      expect(component.stagesValid()).toBe(false);
      expect(stageItems()).toHaveLength(0);
    });

    it("should rebuild the stage items when a template replaces the stages", () => {
      policyServiceMock.templates.set([
        {
          key: "brute-force",
          description: "Locks after repeated failures",
          policy: {
            ...EMPTY_TEMPLATE_POLICY,
            stages: [
              { failure_threshold: 3, actions: [lock] },
              { failure_threshold: 9, actions: [] }
            ]
          }
        }
      ]);
      component.applyTemplate("brute-force");
      fixture.detectChanges();
      expect(stageItems().map((item) => thresholdOf(item).value)).toEqual(["3", "9"]);
    });

    it("should show a conflict on the action and block saving", () => {
      policyServiceMock.actionConflict.mockReturnValue("duplicate");
      withStages([{ failure_threshold: 5, actions: [lock, lock] }]);
      expect(component.stageActionsValid()).toBe(false);
      expect(component.canSave()).toBe(false);
      expect(fixture.nativeElement.querySelector(".ca-action-target-error").textContent).toContain(
        "already on this stage"
      );
      expect(stageNotes().join(" ")).toContain("A stage carries the same action twice");
    });

    it("should show what an action is missing next to it and block saving", () => {
      withStages([{ failure_threshold: 5, actions: [{ action_type: "LOCK_USER", action_value: null }] }]);
      expect(component.actionValuesValid()).toBe(false);
      expect(fixture.nativeElement.querySelector(".ca-action-stale").textContent).toContain("duration");
      expect(component.canSave()).toBe(false);
    });

    describe("typing a change and then the original value back", () => {
      let warn: jest.SpyInstance;
      beforeEach(() => {
        warn = jest.spyOn(console, "warn").mockImplementation(() => undefined);
      });
      afterEach(() => warn.mockRestore());

      const actionPanel = () =>
        fixture.nativeElement.querySelector("mat-expansion-panel.ca-action-item") as HTMLElement;
      const nameInput = () => fixture.nativeElement.querySelector(".ca-stage-name-field input") as HTMLInputElement;
      const loggedRecreation = () => warn.mock.calls.some((args) => String(args[0]).includes("NG0956"));

      it("should keep the stage item, its action panel and the focus when the threshold is typed back", () => {
        const [item] = stageItems();
        const panel = actionPanel();
        (panel.querySelector("mat-expansion-panel-header") as HTMLElement).click();
        fixture.detectChanges();
        expect(panel.classList).not.toContain("mat-expanded");
        const threshold = thresholdOf(item);
        threshold.focus();

        typeInStage(threshold, "7");
        expect(component.hasChanges()).toBe(true);
        typeInStage(threshold, "5");
        expect(component.hasChanges()).toBe(false);

        expect(stageItems()[0]).toBe(item);
        expect(thresholdOf(stageItems()[0])).toBe(threshold);
        expect(actionPanel()).toBe(panel);
        expect(panel.classList).not.toContain("mat-expanded");
        expect(document.activeElement).toBe(threshold);
        expect(loggedRecreation()).toBe(false);
      });

      it("should keep the stage item when the policy name is typed back", () => {
        const [item] = stageItems();
        typeInto(fixture, "Name", "Renamed");
        expect(component.hasChanges()).toBe(true);
        typeInto(fixture, "Name", "Brute Force");
        expect(component.hasChanges()).toBe(false);

        expect(stageItems()[0]).toBe(item);
        expect(loggedRecreation()).toBe(false);
      });

      it("should keep the stage item when the stage name is typed back", () => {
        const [item] = stageItems();
        typeInStage(nameInput(), "Warn");
        typeInStage(nameInput(), "");
        expect(component.hasChanges()).toBe(false);

        expect(stageItems()[0]).toBe(item);
        expect(loggedRecreation()).toBe(false);
      });

      it("should still load the policy when the list arrives while nothing is edited", () => {
        const [item] = stageItems();
        policyServiceMock.policies.set([{ ...mockPolicy, name: "Renamed elsewhere" }]);
        fixture.detectChanges();
        expect(component.editPolicy().name).toBe("Renamed elsewhere");
        expect(stageItems()[0]).not.toBe(item);
      });

      it("should keep an edit when the list arrives while the policy is edited", () => {
        typeInStage(thresholdOf(stageItems()[0]), "7");
        policyServiceMock.policies.set([{ ...mockPolicy, name: "Renamed elsewhere" }]);
        fixture.detectChanges();
        expect(component.editPolicy().name).toBe("Brute Force");
        expect(component.editPolicy().stages[0].failure_threshold).toBe(7);
      });
    });

    it("should write an edited action value to the policy", () => {
      const durationInput = fixture.nativeElement.querySelector(".ca-action-value input") as HTMLInputElement;
      typeInStage(durationInput, "30");
      expect(component.editPolicy().stages[0].actions[0].action_value).toBe(1800);
      expect(component.hasChanges()).toBe(true);
    });
  });

  it("should resolve false and not navigate when save fails", async () => {
    policyServiceMock.savePolicy.mockResolvedValueOnce(undefined);
    routerMock.navigateByUrl.mockClear();
    const result = await component.savePolicy();
    expect(result).toBe(false);
    expect(routerMock.navigateByUrl).not.toHaveBeenCalled();
  });

  it("should send one request for two saves in a row and allow the save again when it fails", async () => {
    patchPolicy(component, { name: "Fresh" });
    let finish!: (id: number | undefined) => void;
    policyServiceMock.savePolicy.mockClear();
    policyServiceMock.savePolicy.mockReturnValueOnce(new Promise<number | undefined>((resolve) => (finish = resolve)));

    const first = component.savePolicy();
    expect(component.canSave()).toBe(false);
    expect(await component.savePolicy()).toBe(false);
    expect(policyServiceMock.savePolicy).toHaveBeenCalledTimes(1);

    finish(undefined);
    expect(await first).toBe(false);
    expect(component.canSave()).toBe(true);
  });

  describe("saving an invalid form", () => {
    beforeEach(() => {
      helpers.setPriority("");
      patchPolicy(component, { name: "" });
      policyServiceMock.savePolicy.mockClear();
    });

    it("should send nothing and report that nothing was saved", async () => {
      expect(await component.savePolicy()).toBe(false);
      expect(policyServiceMock.savePolicy).not.toHaveBeenCalled();
      expect(component.canSave()).toBe(false);
    });

    it("should touch every field so that its error shows", async () => {
      expect(component.policyForm.name().touched()).toBe(false);
      expect(component.policyForm.priority().touched()).toBe(false);

      await component.savePolicy();
      fixture.detectChanges();

      expect(component.policyForm.name().touched()).toBe(true);
      expect(component.policyForm.priority().touched()).toBe(true);
      expect(renderedErrors()).toEqual(expect.arrayContaining(["Name is required.", "Priority is required."]));
    });
  });

  describe("the saving blockers", () => {
    it("should name an emptied stage list", () => {
      setStages(component, []);
      expect(component.saveBlockers()).toEqual(["At least one stage is required."]);
    });

    it("should name a stage carrying contradicting actions", () => {
      policyServiceMock.actionConflict.mockReturnValue("exclusive");
      setStages(component, [{ failure_threshold: 5, actions: [{ action_type: "LOCK_USER", action_value: 60 }] }]);
      expect(component.saveBlockers()).toEqual([
        "A stage carries the same action twice, or two actions that contradict each other."
      ]);
    });

    it("should list the blockers in the order of the form, one line per reason", () => {
      patchPolicy(component, { name: "", counter_types_to_track: [] });
      helpers.setTimeWindow("0");
      helpers.setPriority("");
      setStages(component, [{ failure_threshold: 5, actions: [] }]);
      expect(component.saveBlockers()).toEqual([
        "Name is required.",
        "Time window must be a whole number of at least 1 second.",
        "Priority is required.",
        "At least one tracked event type is required."
      ]);
    });

    it("should render the list while saving is blocked and drop it once it is not", () => {
      const listed = () =>
        Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll(".ca-save-blockers li")).map((li) =>
          li.textContent!.trim()
        );
      helpers.setTimeWindow("0");
      fixture.detectChanges();
      expect(listed()).toEqual(["Time window must be a whole number of at least 1 second."]);

      helpers.setTimeWindow("5");
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector(".ca-save-blockers")).toBeNull();
    });
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

    // An empty list would stringify differently from an absent key, marking a policy that never had conditions as dirty
    // after a condition was added and removed again.
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
      expect(policyServiceMock.savePolicy.mock.calls[0][0].conditions).toMatchObject([
        { condition_type: "USER_REALM", operator: "IN", value: ["sales"] }
      ]);
    });

    // Omitting the key here would leave the stored conditions in place: the backend replaces them only when the key is
    // present, so clearing them takes an explicit empty list.
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
      expect(hasError(component.policyForm.conditions, CA_ERR.staleConditionValue)).toBe(false);
      expect(component.canSave()).toBe(true);
    });

    // The backend rejects a value outside the type's current vocabulary, and since the editor PATCHes the whole policy,
    // without this gate any save of such a policy would fail with a 400.
    it("should be invalid and block saving when a condition names a value that is gone", () => {
      component.onConditionsChange([{ condition_type: "USER_REALM", operator: "IN", value: ["sales", "deleted"] }]);
      expect(hasError(component.policyForm.conditions, CA_ERR.staleConditionValue)).toBe(true);
      expect(component.canSave()).toBe(false);
      expect(component.staleConditionValues()).toEqual([{ condition_type: "USER_REALM", values: ["deleted"] }]);
    });

    it("should list the stale values in the blocker, not the objects that hold them", () => {
      component.onConditionsChange([
        { condition_type: "USER_REALM", operator: "IN", value: ["sales", "gone", "deleted"] }
      ]);
      expect(component.saveBlockers()).toEqual(["A condition names a value that no longer exists: gone, deleted."]);
    });

    it("should not block while the condition vocabulary has not loaded", () => {
      policyServiceMock.conditionTypes.set({});
      component.onConditionsChange([{ condition_type: "USER_REALM", operator: "IN", value: ["deleted"] }]);
      expect(hasError(component.policyForm.conditions, CA_ERR.staleConditionValue)).toBe(false);
    });

    // Dropping a stale value silently would rewrite the policy on load: dropping it from a NOT_IN widens an exemption,
    // and from an IN narrows enforcement, neither of which the admin asked for.
    it("should keep a stale value on the loaded policy instead of dropping it", () => {
      policyServiceMock.policies.set([
        { ...mockPolicy, conditions: [{ condition_type: "USER_REALM", operator: "NOT_IN", value: ["deleted"] }] }
      ]);
      paramMap$.next(convertToParamMap({ id: String(mockPolicy.id) }));
      fixture.detectChanges();
      // toMatchObject rather than toEqual: Signal Forms stamps its own identity symbols onto the objects of the model
      // it wraps, which an exact comparison would trip over.
      expect(component.editPolicy().conditions).toMatchObject([
        { condition_type: "USER_REALM", operator: "NOT_IN", value: ["deleted"] }
      ]);
      expect(component.hasChanges()).toBe(false);
      expect(component.canSave()).toBe(false);
    });
  });

  describe("count floor", () => {
    const withEnforcedSince = (enforcedSince: string | null, timeWindowSeconds = 600) =>
      patchPolicy(component, { enforced_since: enforcedSince, time_window_seconds: timeWindowSeconds });

    it("should not report a floor for a policy that counts its full window", () => {
      withEnforcedSince(null);
      expect(component.countFloorStillBites()).toBe(false);
    });

    it("should report a floor set within the time window", () => {
      withEnforcedSince(new Date(Date.now() - 60_000).toISOString());
      expect(component.countFloorStillBites()).toBe(true);
    });

    // What utc_isoformat actually sends: microsecond precision and a "+00:00" offset, where the
    // Date Time String Format allows three fractional digits. V8 happens to accept it, so this
    // pins the shape the component must keep handling rather than reproducing a visible bug.
    it("should read the microsecond precision the server sends", () => {
      withEnforcedSince(new Date(Date.now() - 60_000).toISOString().replace(/\.(\d{3})Z$/, ".$1789+00:00"));
      expect(component.countFloorStillBites()).toBe(true);
    });

    // Once a full window has passed the backend counts the configured width unchanged, so the hint
    // would only be noise.
    it("should stop reporting a floor older than the time window", () => {
      withEnforcedSince(new Date(Date.now() - 3_600_000).toISOString());
      expect(component.countFloorStillBites()).toBe(false);
    });

    // The trial simulates against the same floor, so dry run does not hide it.
    it("should report a floor while the policy is back in dry run", () => {
      withEnforcedSince(new Date(Date.now() - 60_000).toISOString());
      patchPolicy(component, { dry_run: true });
      expect(component.countFloorStillBites()).toBe(true);
    });
  });
});

describe("ConditionalAccessEditPageComponent — new mode", () => {
  let helpers: ReturnType<typeof fieldHelpers>;
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
        { provide: DialogService, useClass: MockDialogService },
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
    helpers = fieldHelpers(component, fixture);
    fixture.detectChanges();
  });

  it("should start empty and invalid (no name, no counter types, no stages)", () => {
    expect(component.isNewPolicy()).toBe(true);
    expect(component.editPolicy().name).toBe("");
    expect(component.canSave()).toBe(false);
  });

  it("should show the missing-name hint immediately, without the field being touched first", () => {
    expect(component.policyForm.name().touched()).toBe(true);
    // mat-error only renders once the field is touched, so the DOM is checked as well.
    fixture.detectChanges();
    expect(
      Array.from(fixture.nativeElement.querySelectorAll("mat-error")).map((el) =>
        (el as HTMLElement).textContent!.trim()
      )
    ).toContain("Name is required.");
  });

  it("should show the create title", () => {
    expect(component.title()).toEqual("Create Conditional-Access Policy");
  });

  // A policy that does not exist yet has no trial to reset, so switching dry run on and off again
  // while drafting it must not raise the question - and must not send a choice the create call
  // would ignore anyway.
  it("should not ask about the counters while creating a policy", async () => {
    const dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    dialogServiceMock.openDialogAsync = jest.fn();
    component.toggleDryRun(true);

    await component.toggleDryRun(false);

    expect(dialogServiceMock.openDialogAsync).not.toHaveBeenCalled();
    expect(component.editPolicy().dry_run).toBe(false);
    expect(component.editPolicy().reset_counters_on_enforce).toBeUndefined();
  });

  it("should not show the enabled toggle affordance calls without an id", () => {
    component.toggleEnabled(true);
    expect(policyServiceMock.enablePolicy).not.toHaveBeenCalled();
    expect(policyServiceMock.disablePolicy).not.toHaveBeenCalled();
  });

  it("should become valid once name, a counter type, a stage and a priority are set", () => {
    patchPolicy(component, { name: "New Policy" });
    helpers.setCounterTypes(["PIN_FAIL"]);
    setStages(component, [{ failure_threshold: 5, actions: [] }]);
    helpers.setPriority("1");
    expect(component.canSave()).toBe(true);
  });

  it("should stay invalid until a priority is entered (no default)", () => {
    patchPolicy(component, { name: "New Policy" });
    helpers.setCounterTypes(["PIN_FAIL"]);
    setStages(component, [{ failure_threshold: 5, actions: [] }]);
    expect(component.editPolicy().priority).toBeNull();
    expect(hasError(component.policyForm.priority, ERR.required)).toBe(true);
    expect(component.canSave()).toBe(false);
    helpers.setPriority("1");
    expect(component.policyForm.priority().valid()).toBe(true);
    expect(component.canSave()).toBe(true);
  });

  it("should block saving when the priority collides with an existing policy", () => {
    policyServiceMock.policies.set([{ ...mockPolicy, id: 99, priority: 3 }]);
    patchPolicy(component, { name: "New Policy" });
    helpers.setCounterTypes(["PIN_FAIL"]);
    setStages(component, [{ failure_threshold: 5, actions: [] }]);
    helpers.setPriority("3");
    expect(hasError(component.policyForm.priority, CA_ERR.priorityTaken)).toBe(true);
    expect(component.priorityConflict()?.name).toBe("Brute Force");
    expect(component.canSave()).toBe(false);
    // a free priority number clears the collision
    helpers.setPriority("4");
    expect(hasError(component.policyForm.priority, CA_ERR.priorityTaken)).toBe(false);
    expect(component.canSave()).toBe(true);
  });

  it("should show the required hints of the empty fields from the start", () => {
    expect(component.policyForm.priority().touched()).toBe(true);
    expect(component.policyForm.counter_types_to_track().touched()).toBe(true);
    expect(
      Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll("mat-error")).map((el) => el.textContent!.trim())
    ).toEqual(
      expect.arrayContaining([
        "Name is required.",
        "Priority is required.",
        "At least one event type is required. A policy that counts nothing never trips."
      ])
    );
  });

  it("should not offer delete for a new (unsaved) policy", async () => {
    await component.deletePolicy();
    expect(policyServiceMock.deleteWithConfirmDialog).not.toHaveBeenCalled();
  });

  describe("a copy of a policy", () => {
    const draft = (): ConditionalAccessPolicySaveParams => ({
      ...mockPolicy,
      id: undefined,
      priority: null,
      enforced_since: null,
      time_window_seconds: 7200
    });
    const openWithDraft = (): ConditionalAccessEditPageComponent => {
      history.replaceState({ copyOf: draft() }, "");
      const copyFixture = TestBed.createComponent(ConditionalAccessEditPageComponent);
      copyFixture.detectChanges();
      return copyFixture.componentInstance;
    };

    afterEach(() => history.replaceState(null, ""));

    it("should prefill the editor from the draft", () => {
      policyServiceMock.policies.set([]);
      const copy = openWithDraft();

      expect(copy.isNewPolicy()).toBe(true);
      expect(copy.editPolicy()).toEqual(expect.objectContaining({ name: "Brute Force", target: "user" }));
      expect(copy.editPolicy().stages).toMatchObject(mockPolicy.stages);
      expect(copy.policyForm.time_window_value().value()).toBe("2");
      expect(copy.policyForm.time_window_unit().value()).toBe("hours");
    });

    it("should leave the priority empty, because a priority belongs to one policy only", () => {
      const copy = openWithDraft();

      expect(copy.policyForm.priority().value()).toBe("");
      expect(hasError(copy.policyForm.priority, ERR.required)).toBe(true);
      expect(copy.canSave()).toBe(false);
    });

    it("should report the name of the original as taken until it is changed", () => {
      policyServiceMock.policies.set([mockPolicy]);
      const copy = openWithDraft();

      expect(copy.nameConflict()?.id).toBe(mockPolicy.id);
      expect(copy.policyForm.name().touched()).toBe(true);

      patchPolicy(copy, { name: "Brute Force 2", priority: 9 });
      expect(copy.nameConflict()).toBeUndefined();
      expect(copy.canSave()).toBe(true);
    });

    it("should count as a change, so that leaving the page asks about it", () => {
      expect(openWithDraft().hasChanges()).toBe(true);
    });

    it("should consume the draft, so that a later visit of the history entry starts empty", () => {
      openWithDraft();
      expect(history.state?.copyOf).toBeUndefined();

      const revisited = TestBed.createComponent(ConditionalAccessEditPageComponent);
      revisited.detectChanges();
      expect(revisited.componentInstance.editPolicy().name).toBe("");
    });

    it("should start empty without a draft", () => {
      history.replaceState(null, "");
      const empty = TestBed.createComponent(ConditionalAccessEditPageComponent);
      empty.detectChanges();
      expect(empty.componentInstance.editPolicy().name).toBe("");
    });
  });

  describe("name conflict", () => {
    const templateNamed = (name: string) => ({
      key: "tpl",
      description: "",
      policy: { ...EMPTY_TEMPLATE_POLICY, name }
    });

    beforeEach(() => {
      policyServiceMock.policies.set([{ ...mockPolicy, id: 7, name: "Password Brute-Force", priority: 3 }]);
    });

    it("should not report a conflict for the empty name of a new policy", () => {
      expect(component.nameConflict()).toBeUndefined();
    });

    it("should show the error message at once when a template brings the name of an existing policy", () => {
      policyServiceMock.templates.set([templateNamed("Password Brute-Force")]);

      component.applyTemplate("tpl");
      fixture.detectChanges();

      expect(component.nameConflict()?.id).toBe(7);
      expect(component.policyForm.name().touched()).toBe(true);
      expect(fixture.nativeElement.textContent).toContain('A policy named "Password Brute-Force" already exists.');
    });

    it("should block saving a policy under the name of an existing one", () => {
      policyServiceMock.templates.set([templateNamed("password brute-force")]);

      component.applyTemplate("tpl");

      expect(component.canSave()).toBe(false);
      expect(component.saveBlockers()).toContain("A policy with this name already exists.");
    });

    it("should not report a conflict for a template with a free name", () => {
      policyServiceMock.templates.set([templateNamed("Free Name")]);

      component.applyTemplate("tpl");
      fixture.detectChanges();

      expect(component.nameConflict()).toBeUndefined();
      expect(fixture.nativeElement.textContent).not.toContain("already exists");
    });

    it("should clear the conflict when the template is cleared", () => {
      policyServiceMock.templates.set([templateNamed("Password Brute-Force")]);
      component.applyTemplate("tpl");
      expect(component.nameConflict()).toBeDefined();

      component.clearTemplateSelection();

      expect(component.nameConflict()).toBeUndefined();
    });
  });

  describe("the bound controls", () => {
    beforeEach(() => {
      policyServiceMock.eventTypes.set(["PIN_FAIL", "PASSWORD_FAIL"]);
      policyServiceMock.countModesByTarget.set({
        user: ["PER_ATTEMPT", "PER_REQUEST"],
        source_ip: ["DISTINCT_USERS", "PER_ATTEMPT", "PER_REQUEST"]
      });
      fixture.detectChanges();
    });

    it("should write the picked target to the model and mark the field dirty", async () => {
      expect(component.policyForm.target().dirty()).toBe(false);
      await pickOption(fixture, "Target", 1);
      expect(component.policyForm.target().value()).toBe("source_ip");
      expect(component.policyForm.target().dirty()).toBe(true);
      expect(component.editPolicy().target).toBe("source_ip");
    });

    it("should clear and disable the reset checkbox once a source-IP target is picked", async () => {
      await pickOption(fixture, "Target", 1);
      const checkbox: HTMLInputElement = fixture.nativeElement.querySelector(".ca-reset-on-success input");
      expect(component.editPolicy().reset_on_success).toBe(false);
      expect(checkbox.disabled).toBe(true);
      expect(checkbox.checked).toBe(false);
    });

    it("should write the picked count mode and unit to the model", async () => {
      await pickOption(fixture, "Count Mode", 0);
      expect(component.editPolicy().count_mode).toBe("PER_ATTEMPT");
      await pickOption(fixture, "Unit", 2);
      expect(component.policyForm.time_window_unit().value()).toBe("hours");
      expect(component.editPolicy().time_window_seconds).toBe(10 * 3600);
    });

    it("should write the picked event types to the model as a list", async () => {
      await pickOption(fixture, "Tracked event types", 0);
      await pickOption(fixture, "Tracked event types", 1);
      expect(component.editPolicy().counter_types_to_track).toEqual(["PIN_FAIL", "PASSWORD_FAIL"]);
      expect(component.policyForm.counter_types_to_track().dirty()).toBe(true);
    });

    it("should write the reset checkbox to the model when it is clicked", () => {
      const checkbox: HTMLInputElement = fixture.nativeElement.querySelector(".ca-reset-on-success input");
      expect(checkbox.checked).toBe(true);
      checkbox.click();
      fixture.detectChanges();
      expect(component.policyForm.reset_on_success().value()).toBe(false);
      expect(component.policyForm.reset_on_success().dirty()).toBe(true);
    });

    it("should report a priority the browser cannot parse next to the required rule", () => {
      rejectInputAsNumber(inputOf(fixture, "Priority"));
      typeInto(fixture, "Priority", "");
      expect(errorKinds(component.policyForm.priority)).toEqual(expect.arrayContaining([ERR.parse, ERR.required]));
      expect(
        Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll("mat-error")).map((el) => el.textContent!.trim())
      ).toContain("Enter a valid number.");
    });
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
          stages: [{ failure_threshold: 10, actions: [{ action_type: "LOCK_USER", action_value: 600 }] }]
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

    const applyAndReadActionTypes = (rights: string[]): ConditionalAccessActionType[] => {
      const authService = TestBed.inject(AuthService) as unknown as MockAuthService;
      authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights });
      component.applyTemplate("mfa_bruteforce");
      return component.editPolicy().stages[0].actions.map((action) => action.action_type);
    };

    it("prefills it for an admin who may read the SMTP configuration", () => {
      expect(applyAndReadActionTypes(["smtpserver_read"])).toEqual(["LOCK_USER", "EMAIL_ADMIN"]);
    });

    // The email action stays offered without the right; the identifier field becomes free text explaining why the
    // configured servers cannot be listed.
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
    helpers.setTarget("source_ip");
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

  describe("stageActionsValid", () => {
    const stageWith = (...actionTypes: ConditionalAccessActionType[]) => [
      {
        failure_threshold: 5,
        priority: 1,
        actions: actionTypes.map((actionType) => ({ action_type: actionType, action_value: null }))
      }
    ];

    // stageActionsValid() ANDs policyService.actionConflict(...) === null across every action of every stage;
    // which pairs actually conflict is the policy service's own rule, covered against the real implementation
    // in conditional-access-policy.service.spec.ts, so here the mock is just told what to answer.

    it("should accept distinct actions on one stage", () => {
      policyServiceMock.actionConflict.mockReturnValue(null);
      setStages(component, stageWith("LOCK_USER", "EMAIL_ADMIN"));
      expect(component.stageActionsValid()).toBe(true);
    });

    it("should block saving a stage carrying the same action twice", () => {
      policyServiceMock.actionConflict.mockImplementation((_actions: unknown[], index: number) =>
        index === 1 ? "duplicate" : null
      );
      setStages(component, stageWith("LOCK_USER", "LOCK_USER"));
      expect(component.stageActionsValid()).toBe(false);
      expect(component.canSave()).toBe(false);
    });

    it("should block saving a stage carrying two contradicting actions", () => {
      policyServiceMock.actionConflict.mockImplementation((_actions: unknown[], index: number) =>
        index === 1 ? "exclusive" : null
      );
      setStages(component, stageWith("LOCK_USER", "PERMANENT_LOCK_USER"));
      expect(component.stageActionsValid()).toBe(false);
    });

    it("should render the stage-conflict error naming only the real exclusive pairs", () => {
      // There is no ALLOW action type (the pre-auth verdict is DENY/CONTINUE, not a stage action), so the
      // rendered hint must not claim a stage can be invalid for "both allow and deny".
      policyServiceMock.actionConflict.mockImplementation((_actions: unknown[], index: number) =>
        index === 1 ? "exclusive" : null
      );
      setStages(component, stageWith("LOCK_USER", "PERMANENT_LOCK_USER"));
      fixture.detectChanges();
      const errorText = fixture.nativeElement.querySelector(".ca-stages-error")?.textContent ?? "";
      expect(errorText).not.toContain("allow");
      expect(errorText).toContain("lock temporarily and permanently");
      expect(errorText).toContain("block temporarily and permanently");
    });

    it("should not block while no rules have been served", () => {
      policyServiceMock.actionConflict.mockReturnValue(null);
      setStages(component, stageWith("LOCK_USER", "LOCK_USER"));
      expect(component.stageActionsValid()).toBe(true);
    });
  });

  describe("actionValuesValid", () => {
    // Mirrors the backend's _ACTION_VALUE_VALIDATORS: an action whose value the engine could not act on is a
    // 400 on save, so the editor blocks it and says why instead of letting the round-trip fail.
    const stageWithValue = (actionValue: unknown) => [
      {
        failure_threshold: 5,
        actions: [{ action_type: "LOCK_USER" as ConditionalAccessActionType, action_value: actionValue }]
      }
    ];

    it("should block saving while a restricting action has no duration", () => {
      setStages(component, stageWithValue(null));
      expect(component.actionValuesValid()).toBe(false);
      expect(component.canSave()).toBe(false);
    });

    it("should allow saving once the duration is set", () => {
      setStages(component, stageWithValue(600));
      expect(component.actionValuesValid()).toBe(true);
    });
  });

  describe("targetActionsValid", () => {
    const stageWith = (actionType: ConditionalAccessActionType) => [
      { failure_threshold: 5, actions: [{ action_type: actionType, action_value: null }] }
    ];

    beforeEach(() => {
      policyServiceMock.actionsByTarget.set({
        user: ["LOCK_USER", "DENY"],
        source_ip: ["BLOCK_IP", "DENY"]
      });
    });

    it("should be valid when every stage action is allowed for the target", () => {
      helpers.setTarget("user");
      setStages(component, stageWith("LOCK_USER"));
      expect(component.targetActionsValid()).toBe(true);
    });

    it("should be invalid when a stage action is not allowed for the target", () => {
      helpers.setTarget("source_ip");
      setStages(component, stageWith("LOCK_USER"));
      expect(component.targetActionsValid()).toBe(false);
      expect(component.canSave()).toBe(false);
    });

    it("should not block while the allowed-actions list is still empty", () => {
      policyServiceMock.actionsByTarget.set({} as Record<ConditionalAccessTarget, ConditionalAccessActionType[]>);
      policyServiceMock.actionTypes.set([]);
      helpers.setTarget("source_ip");
      setStages(component, stageWith("LOCK_USER"));
      expect(component.targetActionsValid()).toBe(true);
    });
  });

  describe("reset on success", () => {
    it("should update reset_on_success on change", () => {
      helpers.setResetOnSuccess(false);
      expect(component.editPolicy().reset_on_success).toBe(false);
      helpers.setResetOnSuccess(true);
      expect(component.editPolicy().reset_on_success).toBe(true);
    });

    // A source-IP policy aggregates across accounts, so the setting is inert there: the control stays
    // visible - so the target change explains itself - but cannot be operated.
    it("should not apply to a source-IP policy", () => {
      helpers.setTarget("source_ip");
      expect(component.policyForm.reset_on_success().disabled()).toBe(true);
      helpers.setTarget("user");
      expect(component.policyForm.reset_on_success().disabled()).toBe(false);
    });

    // The setting is inert for a source-IP policy, so it is cleared rather than left describing a reset that
    // never happens. It stays cleared on the way back, where the control is enabled again.
    it("should clear the checkbox when the target changes", () => {
      expect(component.editPolicy().reset_on_success).toBe(true);
      helpers.setTarget("source_ip");
      expect(component.editPolicy().reset_on_success).toBe(false);
      helpers.setTarget("user");
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
      expect(component.policyForm.reset_on_success().disabled()).toBe(true);
    });

    it("should render the checkbox disabled for a source-IP policy", () => {
      helpers.setTarget("source_ip");
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
      policyServiceMock.countModesByTarget.set({} as Record<ConditionalAccessTarget, CountMode[]>);
      expect(component.countModeOptions()).toEqual([component.editPolicy().count_mode]);
    });

    it("should offer the target's count modes once loaded", () => {
      helpers.setTarget("source_ip");
      expect(component.countModeOptions()).toEqual(["DISTINCT_USERS", "PER_ATTEMPT", "PER_REQUEST"]);
    });

    it("should update the count mode on change", () => {
      helpers.setCountMode("PER_ATTEMPT");
      expect(component.editPolicy().count_mode).toBe("PER_ATTEMPT");
    });

    it("should not change the count mode when the target changes", () => {
      helpers.setTarget("source_ip");
      helpers.setCountMode("DISTINCT_USERS");
      // Switching to a target where the mode is still valid leaves it untouched...
      helpers.setTarget("source_ip");
      expect(component.editPolicy().count_mode).toBe("DISTINCT_USERS");
      // ...and switching to one where it is invalid also leaves it untouched (surfaced as an error, not rewritten).
      helpers.setTarget("user");
      expect(component.editPolicy().count_mode).toBe("DISTINCT_USERS");
    });

    it("should be valid when the count mode is supported by the target", () => {
      helpers.setTarget("source_ip");
      helpers.setCountMode("PER_ATTEMPT");
      expect(component.policyForm.count_mode().errors()).toEqual([]);
    });

    it("should be invalid and block saving when the count mode is not supported by the target", () => {
      helpers.setTarget("source_ip");
      helpers.setCountMode("DISTINCT_USERS");
      helpers.setTarget("user");
      expect(errorKinds(component.policyForm.count_mode)).toEqual([CA_ERR.countModeNotAllowed]);
      expect(component.canSave()).toBe(false);
    });

    it("should not block while the supported-modes list is still empty", () => {
      policyServiceMock.countModesByTarget.set({} as Record<ConditionalAccessTarget, CountMode[]>);
      helpers.setTarget("user");
      helpers.setCountMode("DISTINCT_USERS");
      expect(component.policyForm.count_mode().errors()).toEqual([]);
    });

    it("should require a count mode and render the message once the select is touched", () => {
      component["policyModel"].update((model) => ({ ...model, count_mode: "" as CountMode }));
      component.policyForm.count_mode().markAsTouched();
      fixture.detectChanges();
      expect(errorKinds(component.policyForm.count_mode)).toEqual([ERR.required]);
      expect(component.saveBlockers()).toContain("Count Mode is required.");
      expect(fixture.nativeElement.textContent).toContain("Count Mode is required.");
    });

    it("should render the not-allowed message once the select is touched", () => {
      helpers.setTarget("source_ip");
      helpers.setCountMode("DISTINCT_USERS");
      helpers.setTarget("user");
      component.policyForm.count_mode().markAsTouched();
      fixture.detectChanges();
      expect(fixture.nativeElement.textContent).toContain("This count mode is not allowed for the selected target.");
    });

    it("should label the count modes", () => {
      expect(component.countModeLabel("PER_REQUEST")).toBe("Per Request");
      expect(component.countModeLabel("DISTINCT_USERS")).toBe("Distinct Users");
      expect(component.countModeLabel("WHATEVER")).toBe("WHATEVER");
    });
  });
});
