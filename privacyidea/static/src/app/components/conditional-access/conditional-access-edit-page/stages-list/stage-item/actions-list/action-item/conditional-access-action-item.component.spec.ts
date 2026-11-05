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
import { signal, WritableSignal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FieldTree, form } from "@angular/forms/signals";
import { AuthService } from "@services/auth/auth.service";
import { applyActionRules } from "@services/conditional-access/conditional-access-policy-form";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessActionType,
  ConditionalAccessStageAction,
  ConditionalAccessTarget
} from "@services/conditional-access/conditional-access-policy.service";
import { SmtpServer, SmtpService } from "@services/smtp/smtp.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockConditionalAccessPolicyService } from "@testing/mock-services/mock-conditional-access-policy-service";
import { MockSmtpService } from "@testing/mock-services/mock-smtp-service";
import { ConditionalAccessActionItemComponent } from "./conditional-access-action-item.component";

describe("ConditionalAccessActionItemComponent", () => {
  let component: ConditionalAccessActionItemComponent;
  let fixture: ComponentFixture<ConditionalAccessActionItemComponent>;
  let authService: MockAuthService;
  let smtpService: MockSmtpService;
  let model: WritableSignal<{ target: ConditionalAccessTarget; actions: ConditionalAccessStageAction[] }>;
  let actionFields: FieldTree<ConditionalAccessStageAction[]>;

  // The action in the policy form the item is bound to, judged by the rules of the form.
  function setAction(action: ConditionalAccessStageAction): void {
    model.update((current) => ({ ...current, actions: [{ ...action }] }));
    fixture.componentRef.setInput("action", actionFields[0]);
    fixture.detectChanges();
  }

  // The target of the policy the action belongs to, which the form rules and the select options both read.
  function setTarget(target: ConditionalAccessTarget): void {
    model.update((current) => ({ ...current, target }));
    fixture.componentRef.setInput("target", target);
  }

  // The action as the form holds it.
  const stored = (): ConditionalAccessStageAction => model().actions[0];

  // A new item, as the editor creates one for an action it loads - the unit is picked from the first duration it shows.
  function createWithAction(action: ConditionalAccessStageAction): void {
    // The earlier item is still bound to the action this one replaces, and a field of a replaced action cannot be read.
    fixture.destroy();
    fixture = TestBed.createComponent(ConditionalAccessActionItemComponent);
    component = fixture.componentInstance;
    setAction(action);
  }

  function setRights(rights: string[]): void {
    authService.authData.set({ ...MockAuthService.MOCK_AUTH_DATA, rights });
    fixture.detectChanges();
  }

  function smtpServer(identifier: string): SmtpServer {
    return {
      identifier,
      server: "mail.example.com",
      port: 25,
      timeout: 120,
      sender: "",
      tls: false,
      enqueue_job: false,
      smime: false,
      dont_send_on_error: true
    };
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessActionItemComponent],
      providers: [
        { provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SmtpService, useClass: MockSmtpService }
      ]
    }).compileComponents();

    const policyServiceMock = TestBed.inject(
      ConditionalAccessPolicyService
    ) as unknown as MockConditionalAccessPolicyService;
    model = signal({
      target: "user" as ConditionalAccessTarget,
      actions: [{ action_type: "LOCK_USER" as const, action_value: 600 }]
    });
    actionFields = TestBed.runInInjectionContext(() =>
      form(model, (p) => applyActionRules(p.actions, p.target, policyServiceMock))
    ).actions;
    fixture = TestBed.createComponent(ConditionalAccessActionItemComponent);
    component = fixture.componentInstance;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    smtpService = TestBed.inject(SmtpService) as unknown as MockSmtpService;
    setAction({ action_type: "LOCK_USER", action_value: 600 });
    // The rights of a default install, where no admin policy narrows them.
    setRights(["smtpserver_read"]);
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should describe every action type", () => {
    for (const type of ["LOCK_USER", "PERMANENT_LOCK_USER", "BLOCK_IP", "DENY", "EMAIL_USER"] as const) {
      setAction({ action_type: type, action_value: null });
      expect(component.actionDescription().length).toBeGreaterThan(0);
    }
  });

  it("should classify the value mode from the action type", () => {
    setAction({ action_type: "LOCK_USER", action_value: 600 });
    expect(component.valueMode()).toBe("duration");
    setAction({ action_type: "EMAIL_ADMIN", action_value: {} });
    expect(component.valueMode()).toBe("email");
    setAction({ action_type: "DENY", action_value: null });
    expect(component.valueMode()).toBe("none");
  });

  describe("target compatibility", () => {
    let policyServiceMock: MockConditionalAccessPolicyService;

    beforeEach(() => {
      policyServiceMock = TestBed.inject(
        ConditionalAccessPolicyService
      ) as unknown as MockConditionalAccessPolicyService;
      policyServiceMock.actionsByTarget.set({
        user: ["LOCK_USER", "PERMANENT_LOCK_USER", "EMAIL_ADMIN", "EMAIL_USER", "DENY"],
        source_ip: ["BLOCK_IP", "PERMANENT_BLOCK_IP", "EMAIL_ADMIN", "DENY"]
      });
    });

    it("flags an action that is not allowed for the current target", () => {
      setTarget("source_ip");
      setAction({ action_type: "LOCK_USER", action_value: 600 });
      expect(component.isActionAllowedForTarget()).toBe(false);
      // the stale type stays selectable so the user can change it
      expect(component.allowedActionTypes()).toContain("LOCK_USER");
    });

    it("accepts an action that is allowed for the current target", () => {
      setTarget("source_ip");
      setAction({ action_type: "BLOCK_IP", action_value: 600 });
      expect(component.isActionAllowedForTarget()).toBe(true);
    });

    it("does not flag while the allowed list is still empty", () => {
      policyServiceMock.actionsByTarget.set({} as Record<ConditionalAccessTarget, ConditionalAccessActionType[]>);
      policyServiceMock.actionTypes.set([]);
      setTarget("source_ip");
      setAction({ action_type: "LOCK_USER", action_value: 600 });
      expect(component.isActionAllowedForTarget()).toBe(true);
    });
  });

  // The component's own job here is showing the verdict the form rules reached for this action and mapping the
  // sibling list to the disabled-types set. The rules themselves (which actions are repeatable, which pairs are
  // exclusive) are the policy service's, and are covered once, against the real implementation, in
  // conditional-access-policy.service.spec.ts.
  describe("stage action combinations", () => {
    let policyServiceMock: MockConditionalAccessPolicyService;
    const action = (actionType: ConditionalAccessActionType) => ({ action_type: actionType, action_value: null });

    beforeEach(() => {
      policyServiceMock = TestBed.inject(
        ConditionalAccessPolicyService
      ) as unknown as MockConditionalAccessPolicyService;
    });

    // The item at `index` of a stage carrying `siblings`.
    const withSiblings = (siblings: ConditionalAccessStageAction[], index: number) => {
      model.update((current) => ({ ...current, actions: siblings.map((sibling) => ({ ...sibling })) }));
      fixture.componentRef.setInput("action", actionFields[index]);
      fixture.componentRef.setInput("siblingActions", model().actions);
      fixture.componentRef.setInput("actionIndex", index);
      fixture.detectChanges();
    };

    it("shows the message for a duplicate and asks about the action at its own index", () => {
      policyServiceMock.actionConflict.mockReturnValue("duplicate");
      withSiblings([action("LOCK_USER"), action("LOCK_USER")], 1);
      expect(component.conflictMessage()).toContain("already on this stage");
      expect(fixture.nativeElement.querySelector(".ca-action-target-error").textContent).toContain(
        "already on this stage"
      );
      const [actionsAsked, indexAsked, targetAsked] = policyServiceMock.actionConflict.mock.calls.at(-1)!;
      expect(actionsAsked.map((asked) => asked.action_type)).toEqual(["LOCK_USER", "LOCK_USER"]);
      expect([indexAsked, targetAsked]).toEqual([1, "user"]);
    });

    it("shows no message for an action that conflicts with nothing", () => {
      policyServiceMock.actionConflict.mockReturnValue(null);
      withSiblings([action("EMAIL_ADMIN"), action("EMAIL_ADMIN")], 1);
      expect(component.conflictMessage()).toBe("");
      expect(fixture.nativeElement.querySelector(".ca-action-target-error")).toBeNull();
    });

    it("shows the message for an exclusive pair and flags the action", () => {
      policyServiceMock.actionConflict.mockReturnValue("exclusive");
      withSiblings([action("LOCK_USER"), action("PERMANENT_LOCK_USER")], 1);
      expect(component.conflictMessage()).toContain("contradicts");
      expect(fixture.nativeElement.querySelector(".ca-action-warn-icon")).toBeTruthy();
    });

    it("forwards the unavailable-types set from the policy service as disabledActionTypes", () => {
      const siblings = [action("LOCK_USER"), action("EMAIL_ADMIN")];
      policyServiceMock.unavailableActionTypes.mockReturnValue(new Set(["LOCK_USER", "PERMANENT_LOCK_USER"]));
      withSiblings(siblings, 1);
      const disabled = component.disabledActionTypes();
      expect(disabled.has("LOCK_USER")).toBe(true);
      expect(disabled.has("PERMANENT_LOCK_USER")).toBe(true);
      expect(disabled.has("EMAIL_ADMIN")).toBe(false);
      expect(policyServiceMock.unavailableActionTypes).toHaveBeenCalledWith(
        component["siblingActions"](),
        component.target(),
        1
      );
    });

    it("does not judge while no rules have been served", () => {
      policyServiceMock.actionConflict.mockReturnValue(null);
      policyServiceMock.unavailableActionTypes.mockReturnValue(new Set());
      withSiblings([action("LOCK_USER"), action("LOCK_USER")], 1);
      expect(component.conflictMessage()).toBe("");
      expect(component.disabledActionTypes().size).toBe(0);
    });
  });

  describe("duration", () => {
    it("should read a plain-number duration", () => {
      setAction({ action_type: "LOCK_USER", action_value: 90 });
      expect(component.durationValue()).toBe("90");
    });

    it("should show a stored duration in the coarsest unit it is a whole number of", () => {
      createWithAction({ action_type: "LOCK_USER", action_value: 7200 });
      expect(component.durationUnit()).toBe("hours");
      expect(component.durationValue()).toBe("2");
    });

    it("should keep the unit while typing a value a coarser unit divides", () => {
      setAction({ action_type: "LOCK_USER", action_value: 45 });
      expect(component.durationUnit()).toBe("seconds");
      component.onDurationInput("60");
      expect(component.durationUnit()).toBe("seconds");
      expect(component.durationValue()).toBe("60");
    });

    it("should pick the unit afresh for another action's duration, even one the current unit divides", () => {
      setAction({ action_type: "LOCK_USER", action_value: 45 });
      setAction({ action_type: "BLOCK_IP", action_value: 7200 });
      expect(component.durationUnit()).toBe("hours");
      expect(component.durationValue()).toBe("2");
    });

    it("should show a stored zero in seconds", () => {
      createWithAction({ action_type: "LOCK_USER", action_value: 0 });
      expect(component.durationUnit()).toBe("seconds");
    });

    it("should keep the unit when the field is cleared", () => {
      createWithAction({ action_type: "LOCK_USER", action_value: 7200 });
      setAction({ action_type: "LOCK_USER", action_value: null });
      expect(component.durationUnit()).toBe("hours");
    });

    it("should pick the unit afresh for a duration the current unit does not divide", () => {
      createWithAction({ action_type: "LOCK_USER", action_value: 7200 });
      setAction({ action_type: "LOCK_USER", action_value: 90 });
      expect(component.durationUnit()).toBe("seconds");
      expect(component.durationValue()).toBe("90");
    });

    it("should read a nested duration_seconds", () => {
      setAction({ action_type: "LOCK_USER", action_value: { duration_seconds: 30 } });
      expect(component.durationValue()).toBe("30");
    });

    it("should write the parsed integer on input and null when cleared", () => {
      setAction({ action_type: "LOCK_USER", action_value: 90 });
      component.onDurationInput("45");
      expect(stored().action_value).toBe(45);
      component.onDurationInput("");
      expect(stored().action_value).toBeNull();
    });

    it("should write a typed duration from the field", () => {
      setAction({ action_type: "LOCK_USER", action_value: 45 });
      const input = fixture.nativeElement.querySelector(".ca-action-value input") as HTMLInputElement;
      input.value = "30";
      input.dispatchEvent(new Event("input"));
      fixture.detectChanges();
      expect(stored().action_value).toBe(30);
    });

    it("should keep the type and the retrigger choice of an action whose duration is edited", () => {
      setAction({ action_type: "BLOCK_IP", action_value: 90, retrigger_above_threshold: true });
      component.onDurationInput("45");
      expect(stored()).toMatchObject({ action_type: "BLOCK_IP", action_value: 45, retrigger_above_threshold: true });
    });

    it("should convert the entered value to seconds using the selected unit", () => {
      setAction({ action_type: "LOCK_USER", action_value: null });
      component.durationUnit.set("minutes");
      component.onDurationInput("5");
      expect(stored().action_value).toBe(300);
    });

    it("should display the stored seconds in the selected unit", () => {
      setAction({ action_type: "LOCK_USER", action_value: 3600 });
      component.durationUnit.set("hours");
      expect(component.durationValue()).toBe("1");
    });

    it("should keep the entered number and re-scale to seconds on unit change", () => {
      setAction({ action_type: "LOCK_USER", action_value: 90 });
      component.onDurationUnitChange("minutes");
      expect(component.durationUnit()).toBe("minutes");
      // "90" kept and re-interpreted as 90 minutes = 5400s.
      expect(stored().action_value).toBe(5400);
    });

    it("should not write on unit change when there is no value", () => {
      setAction({ action_type: "LOCK_USER", action_value: null });
      component.onDurationUnitChange("hours");
      expect(stored().action_value).toBeNull();
    });

    // A policy written through the API may store the duration as a string; the field must show it rather
    // than looking empty and inviting the admin to overwrite a value that is already there.
    it("should read a numeric-string duration", () => {
      setAction({ action_type: "LOCK_USER", action_value: "90" });
      expect(component.durationValue()).toBe("90");
    });
  });

  // The client-side half of the backend's per-action action_value contract: the message belongs next to the
  // field, not in a 400 after the round-trip.
  describe("actionValueError", () => {
    it("reports a restricting action that has no usable duration", () => {
      for (const actionValue of [null, 0, -5, "600abc", "600.5", { lock_duration_seconds: 600 }]) {
        setAction({ action_type: "LOCK_USER", action_value: actionValue });
        expect(component.actionValueError()).not.toBeNull();
      }
    });

    it("accepts every duration shape the backend stores", () => {
      for (const actionValue of [600, "600", { duration_seconds: 600 }, { duration: 600 }]) {
        setAction({ action_type: "LOCK_USER", action_value: actionValue });
        expect(component.actionValueError()).toBeNull();
      }
    });

    it("reports an email action without a subject and body", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: {} });
      expect(component.actionValueError()).not.toBeNull();
      setAction({ action_type: "EMAIL_ADMIN", action_value: { subject: "Hi" } });
      expect(component.actionValueError()).not.toBeNull();
    });

    it("accepts an email action with a subject and body but no SMTP server yet", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "", subject: "s", body: "b" } });
      expect(component.actionValueError()).toBeNull();
    });

    it("accepts the actions that take no value, and reports one carrying a value", () => {
      setAction({ action_type: "PERMANENT_LOCK_USER", action_value: null });
      expect(component.actionValueError()).toBeNull();
      setAction({ action_type: "DENY", action_value: null });
      expect(component.actionValueError()).toBeNull();
      setAction({ action_type: "PERMANENT_LOCK_USER", action_value: 600 });
      expect(component.actionValueError()).not.toBeNull();
    });
  });

  describe("email", () => {
    it("should include recipient_group only for EMAIL_ADMIN", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: {} });
      expect(component.emailFields().map((f) => f.key)).toContain("recipient_group");
      setAction({ action_type: "EMAIL_USER", action_value: {} });
      expect(component.emailFields().map((f) => f.key)).not.toContain("recipient_group");
    });

    it("should default the mimetype to plain when unset", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: {} });
      expect(component.emailFieldValue("mimetype")).toBe("plain");
      expect(component.emailFieldValue("subject")).toBe("");
    });

    it("should merge a field into the value object", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: { subject: "Hi" } });
      component.onEmailFieldInput("body", "Hello {user}");
      expect(stored().action_value).toEqual({ subject: "Hi", body: "Hello {user}" });
    });

    it("should drop an emptied non-mimetype field", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: { subject: "Hi", body: "x" } });
      component.onEmailFieldInput("body", "");
      expect(stored().action_value).toEqual({ subject: "Hi" });
    });

    it("should keep an emptied mimetype instead of dropping it", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: { subject: "Hi", mimetype: "html" } });
      component.onEmailFieldInput("mimetype", "");
      expect(stored().action_value).toEqual({ subject: "Hi", mimetype: "" });
    });

    it("should store no value once every field is emptied", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: { subject: "Hi" } });
      component.onEmailFieldInput("subject", "");
      expect(stored().action_value).toBeNull();
    });

    it("should clear the missing-value message once the subject and body are written", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: {} });
      expect(component.actionValueError()).not.toBeNull();
      component.onEmailFieldInput("subject", "Hi");
      component.onEmailFieldInput("body", "Hello");
      fixture.detectChanges();
      expect(component.actionValueError()).toBeNull();
      expect(fixture.nativeElement.querySelector(".ca-action-value-error")).toBeNull();
    });

    describe("SMTP server", () => {
      it("offers the configured identifiers as a select", () => {
        smtpService.smtpServers.set([smtpServer("primary"), smtpServer("backup")]);
        setAction({ action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "backup" } });
        expect(component.emailFields().find((field) => field.key === "smtp_identifier")?.kind).toBe("smtp");
        expect(component.smtpOptions()).toEqual(["primary", "backup"]);
        expect(component.staleSmtpIdentifier()).toBe("");
      });

      it("keeps and flags an identifier that is no longer configured", () => {
        smtpService.smtpServers.set([smtpServer("primary")]);
        setAction({ action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "retired" } });
        // Listed, or the select would show a blank trigger for the value the action carries.
        expect(component.smtpOptions()).toEqual(["primary", "retired"]);
        expect(component.staleSmtpIdentifier()).toBe("retired");
      });

      it("flags nothing while no server has been listed yet", () => {
        setAction({ action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "primary" } });
        expect(component.smtpOptions()).toEqual(["primary"]);
        expect(component.staleSmtpIdentifier()).toBe("");
      });

      it("falls back to a plain input with an explaining hint without smtpserver_read", () => {
        setAction({ action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "primary" } });
        setRights([]);
        const field = component.emailFields().find((each) => each.key === "smtp_identifier");
        expect(field?.kind).toBe("text");
        expect(field?.hint).toContain("smtpserver_read");
        // Flagged in the error colour: it reports a missing right, not a description of the field.
        expect(field?.hintWarn).toBe(true);
      });
    });
  });

  describe("email actions without smtpserver_read", () => {
    beforeEach(() => {
      const policyServiceMock = TestBed.inject(
        ConditionalAccessPolicyService
      ) as unknown as MockConditionalAccessPolicyService;
      policyServiceMock.actionsByTarget.set({
        user: ["LOCK_USER", "PERMANENT_LOCK_USER", "EMAIL_ADMIN", "EMAIL_USER", "DENY"],
        source_ip: ["BLOCK_IP", "PERMANENT_BLOCK_IP", "EMAIL_ADMIN", "DENY"]
      });
      setRights([]);
    });

    it("still offers them, only without the server list", () => {
      setAction({ action_type: "LOCK_USER", action_value: 600 });
      expect(component.smtpServersListable()).toBe(false);
      expect(component.allowedActionTypes()).toContain("EMAIL_ADMIN");
      expect(component.allowedActionTypes()).toContain("EMAIL_USER");
      expect(component.allowedActionTypes()).toContain("LOCK_USER");
    });

    it("keeps one the policy already carries valid for its target", () => {
      setAction({ action_type: "EMAIL_ADMIN", action_value: { smtp_identifier: "primary" } });
      expect(component.allowedActionTypes()).toContain("EMAIL_ADMIN");
      // The action is still valid for a user-targeted policy: it is the SMTP config that is out of reach, not the
      // action type, so nothing is flagged as target-incompatible.
      expect(component.isActionAllowedForTarget()).toBe(true);
    });
  });

  it("should reset the value when the type changes to another mode", () => {
    setAction({ action_type: "EMAIL_ADMIN", action_value: { subject: "Hi" } });
    component.onActionTypeChange("LOCK_USER");
    expect(stored()).toMatchObject({ action_type: "LOCK_USER", action_value: null });
  });

  it("should keep the value when the type stays in the same mode", () => {
    setAction({ action_type: "LOCK_USER", action_value: 600 });
    component.onActionTypeChange("BLOCK_IP");
    expect(stored()).toMatchObject({ action_type: "BLOCK_IP", action_value: 600 });
  });

  it("should emit removeAction", () => {
    const spy = jest.spyOn(component.removeAction, "emit");
    component.onRemoveAction();
    expect(spy).toHaveBeenCalled();
  });

  describe("retrigger", () => {
    it("should write the retrigger choice when the checkbox toggles", () => {
      component.onRetriggerChange(true);
      expect(stored().retrigger_above_threshold).toBe(true);
      component.onRetriggerChange(false);
      expect(stored().retrigger_above_threshold).toBe(false);
    });

    it("should write the retrigger choice from the checkbox", () => {
      setAction({ action_type: "LOCK_USER", action_value: 600 });
      (fixture.nativeElement.querySelector("mat-checkbox input") as HTMLInputElement).click();
      fixture.detectChanges();
      expect(stored().retrigger_above_threshold).toBe(true);
    });

    it("should default the checkbox by action type when unset", () => {
      // LOCK_USER defaults to fire-once (unchecked).
      setAction({ action_type: "LOCK_USER", action_value: 600 });
      expect(component.retriggerChecked()).toBe(false);
      // DENY defaults to re-trigger (checked).
      setAction({ action_type: "DENY", action_value: null });
      expect(component.retriggerChecked()).toBe(true);
    });

    it("should honor an explicit value over the action-type default", () => {
      setAction({ action_type: "DENY", action_value: null, retrigger_above_threshold: false });
      expect(component.retriggerChecked()).toBe(false);
      setAction({ action_type: "LOCK_USER", action_value: 600, retrigger_above_threshold: true });
      expect(component.retriggerChecked()).toBe(true);
    });
  });
});
