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
import { AuthService } from "@services/auth/auth.service";
import {
  ConditionalAccessPolicyService,
  DefaultErrorMessage,
  LockoutPolicyStage,
  LockoutStageAction
} from "@services/conditional-access/conditional-access-policy.service";
import { SmtpService } from "@services/smtp/smtp.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockConditionalAccessPolicyService } from "@testing/mock-services/mock-conditional-access-policy-service";
import { MockSmtpService } from "@testing/mock-services/mock-smtp-service";
import { ConditionalAccessStageItemComponent } from "./conditional-access-stage-item.component";

describe("ConditionalAccessStageItemComponent", () => {
  let component: ConditionalAccessStageItemComponent;
  let fixture: ComponentFixture<ConditionalAccessStageItemComponent>;

  const stage: LockoutPolicyStage = {
    failure_threshold: 5,
    priority: 1,
    actions: [{ action_type: "LOCK_USER", action_value: { lock_duration_seconds: 600 } }]
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessStageItemComponent],
      providers: [
        { provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SmtpService, useClass: MockSmtpService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConditionalAccessStageItemComponent);
    fixture.componentRef.setInput("stage", stage);
    fixture.componentRef.setInput("stageNumber", 1);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should emit updateStage for a valid failure_threshold", () => {
    const spy = jest.spyOn(component.updateStage, "emit");
    component.onFailureThresholdInput("10");
    expect(spy).toHaveBeenCalledWith({ failure_threshold: 10 });
  });

  it("should emit updateStage for a threshold of 0 (an allow/deny allowlist stage)", () => {
    const spy = jest.spyOn(component.updateStage, "emit");
    component.onFailureThresholdInput("0");
    expect(spy).toHaveBeenCalledWith({ failure_threshold: 0 });
  });

  it("should not emit for an invalid failure_threshold", () => {
    const spy = jest.spyOn(component.updateStage, "emit");
    component.onFailureThresholdInput("-1");
    expect(spy).not.toHaveBeenCalled();
    component.onFailureThresholdInput("abc");
    expect(spy).not.toHaveBeenCalled();
  });

  it("should emit updateStage when actions change", () => {
    const spy = jest.spyOn(component.updateStage, "emit");
    component.onActionsChange([]);
    expect(spy).toHaveBeenCalledWith({ actions: [] });
  });

  it("should emit removeStage", () => {
    const spy = jest.spyOn(component.removeStage, "emit");
    component.onRemoveStage();
    expect(spy).toHaveBeenCalled();
  });

  it("should emit a trimmed name, or null when blank", () => {
    const spy = jest.spyOn(component.updateStage, "emit");
    component.onNameInput("  Warn user  ");
    expect(spy).toHaveBeenCalledWith({ name: "Warn user" });
    component.onNameInput("   ");
    expect(spy).toHaveBeenCalledWith({ name: null });
  });

  it("should toggle name editing", () => {
    expect(component.editingName()).toBe(false);
    component.startEditingName();
    expect(component.editingName()).toBe(true);
    component.stopEditingName();
    expect(component.editingName()).toBe(false);
  });

  describe("error message", () => {
    const SUGGESTIONS: DefaultErrorMessage[] = [
      { action_type: "PERMANENT_LOCK_USER", category: "restriction", message: "Your account has been locked." },
      { action_type: "LOCK_USER", category: "restriction", message: "Locked. Try again in about {duration}." },
      { action_type: "DENY", category: "restriction", message: "Access has been denied." },
      { action_type: "EMAIL_USER", category: "notification", message: "An email has been sent to you." },
      { action_type: "EMAIL_ADMIN", category: "notification", message: "Your administrator has been notified." }
    ];

    let policyService: MockConditionalAccessPolicyService;

    const withStage = (override: Partial<LockoutPolicyStage>) =>
      fixture.componentRef.setInput("stage", { ...stage, ...override });

    beforeEach(() => {
      policyService = TestBed.inject(ConditionalAccessPolicyService) as unknown as MockConditionalAccessPolicyService;
      policyService.defaultErrorMessages.set(SUGGESTIONS);
    });

    it("should emit the error_message exactly as typed", () => {
      // Not trimmed here: the field is bound back to this value, so trimming would delete a space the
      // admin has just typed. validate_error_message strips it, and treats a blank message as none.
      const spy = jest.spyOn(component.updateStage, "emit");
      component.onErrorMessageInput("  Locked.  ");
      expect(spy).toHaveBeenCalledWith({ error_message: "  Locked.  " });
      component.onErrorMessageInput("   ");
      expect(spy).toHaveBeenCalledWith({ error_message: "   " });
    });

    it("should be off for a stage with no message and on for one that has it", () => {
      withStage({ error_message: null });
      expect(component.showErrorMessage()).toBe(false);
      withStage({ error_message: "Locked." });
      expect(component.showErrorMessage()).toBe(true);
    });

    it("should stay visible while the field is cleared mid-edit", () => {
      // Clearing the textarea leaves an empty message, not an absent one, so the field does not derive
      // itself away the moment the admin selects-all-and-deletes.
      withStage({ error_message: "Locked." });
      component.onErrorMessageInput("");
      withStage({ error_message: "" });
      expect(component.showErrorMessage()).toBe(true);
    });

    it("should emit an empty message rather than null while the field is being cleared", () => {
      withStage({ error_message: "Locked." });
      const spy = jest.spyOn(component.updateStage, "emit");
      component.onErrorMessageInput("");
      expect(spy).toHaveBeenCalledWith({ error_message: "" });
    });

    it("should hide the field only when the stage carries no message at all", () => {
      withStage({ error_message: null });
      expect(component.showErrorMessage()).toBe(false);
      withStage({});
      expect(component.showErrorMessage()).toBe(false);
    });

    it("should fill in the suggestion when switched on", () => {
      withStage({ error_message: null, actions: [{ action_type: "LOCK_USER", action_value: null }] });
      const spy = jest.spyOn(component.updateStage, "emit");
      component.toggleErrorMessage(true);
      expect(spy).toHaveBeenCalledWith({ error_message: "Locked. Try again in about {duration}." });
    });

    it("should suggest one restriction by severity, never two", () => {
      // Restrictions are mutually exclusive - only the longest-lasting one is ever reported - so the
      // most severe wins regardless of the order the actions were added in.
      withStage({
        error_message: null,
        actions: [
          { action_type: "LOCK_USER", action_value: null },
          { action_type: "PERMANENT_LOCK_USER", action_value: null }
        ]
      });
      expect(component.suggestedErrorMessage()).toBe("Your account has been locked.");
    });

    it("should suggest nothing for an action that has no wording", () => {
      // ALLOW rejects nothing, so the server offers no entry for it and there is nothing to reset to.
      withStage({ error_message: null, actions: [{ action_type: "ALLOW", action_value: null }] });
      expect(component.suggestedErrorMessage()).toBeNull();
      expect(component.canResetErrorMessage()).toBe(false);
    });

    it("should suggest the notification wording for a notify-only stage", () => {
      withStage({ error_message: null, actions: [{ action_type: "EMAIL_ADMIN", action_value: null }] });
      expect(component.suggestedErrorMessage()).toBe("Your administrator has been notified.");
    });

    it("should lead with the restriction and append the notification when the stage does both", () => {
      // Being emailed about is a separate fact from being locked out, so the user is told both -
      // matching the notice the engine appends today.
      withStage({
        error_message: null,
        actions: [
          { action_type: "EMAIL_ADMIN", action_value: null },
          { action_type: "LOCK_USER", action_value: null }
        ]
      });
      expect(component.suggestedErrorMessage()).toBe(
        "Locked. Try again in about {duration}. Your administrator has been notified."
      );
    });

    it("should append every notification the stage triggers", () => {
      withStage({
        error_message: null,
        actions: [
          { action_type: "EMAIL_USER", action_value: null },
          { action_type: "EMAIL_ADMIN", action_value: null }
        ]
      });
      expect(component.suggestedErrorMessage()).toBe(
        "An email has been sent to you. Your administrator has been notified."
      );
    });

    it("should clear the message when switched off", () => {
      withStage({ error_message: "Mine." });
      const spy = jest.spyOn(component.updateStage, "emit");
      component.toggleErrorMessage(false);
      expect(spy).toHaveBeenCalledWith({ error_message: null });
      // Visibility follows the stage, so it turns off once the parent has applied that emit - this
      // component keeps no copy of the answer that could disagree with the data.
      withStage({ error_message: null });
      expect(component.showErrorMessage()).toBe(false);
    });

    it("should not carry a message across the stage it was written for", () => {
      // The stages list tracks by $index, so removing a stage rebinds this component to the next one.
      // Nothing about the message is held here, so switching on offers that stage's own suggestion -
      // never text belonging to the stage that was removed.
      withStage({ error_message: "Mine." });
      component.toggleErrorMessage(false);
      withStage({ error_message: null, actions: [{ action_type: "LOCK_USER", action_value: null }] });
      const spy = jest.spyOn(component.updateStage, "emit");
      component.toggleErrorMessage(true);
      expect(spy).toHaveBeenCalledWith({ error_message: "Locked. Try again in about {duration}." });
    });

    it("should switch on with an empty field when the stage has nothing to suggest", () => {
      withStage({ error_message: null, actions: [{ action_type: "ALLOW", action_value: null }] });
      const spy = jest.spyOn(component.updateStage, "emit");
      component.toggleErrorMessage(true);
      expect(spy).toHaveBeenCalledWith({ error_message: "" });
    });

    it("should replace the message with the suggestion on reset", () => {
      withStage({ error_message: "Stale wording.", actions: [{ action_type: "DENY", action_value: null }] });
      const spy = jest.spyOn(component.updateStage, "emit");
      component.resetErrorMessageToSuggestion();
      expect(spy).toHaveBeenCalledWith({ error_message: "Access has been denied." });
    });

    it("should not offer a reset when the message already matches the suggestion", () => {
      withStage({
        error_message: "Access has been denied.",
        actions: [{ action_type: "DENY", action_value: null }]
      });
      expect(component.canResetErrorMessage()).toBe(false);
    });

    it("should offer a reset once the actions no longer match the message", () => {
      withStage({
        error_message: "Access has been denied.",
        actions: [{ action_type: "PERMANENT_LOCK_USER", action_value: null }]
      });
      expect(component.canResetErrorMessage()).toBe(true);
    });

    it("should move the suggestion but not the authored message when actions change", () => {
      // The suggestion follows the stage's actions; the admin's own wording is never overwritten by
      // them, so the reset button becomes the only way to adopt the new one.
      withStage({ error_message: "Mine.", actions: [{ action_type: "LOCK_USER", action_value: null }] });
      expect(component.suggestedErrorMessage()).toBe("Locked. Try again in about {duration}.");

      const spy = jest.spyOn(component.updateStage, "emit");
      const actions: LockoutStageAction[] = [{ action_type: "PERMANENT_LOCK_USER", action_value: null }];
      component.onActionsChange(actions);
      // Only the actions travel: an error_message key here would mean the wording was regenerated.
      expect(spy).toHaveBeenCalledWith({ actions });

      withStage({ error_message: "Mine.", actions });
      expect(component.suggestedErrorMessage()).toBe("Your account has been locked.");
      expect(component.stage().error_message).toBe("Mine.");
      expect(component.canResetErrorMessage()).toBe(true);
    });

    it("should not flag {duration} as unknown", () => {
      withStage({ error_message: "Try again in about {duration}." });
      expect(component.unknownTags()).toEqual([]);
    });

    it("should flag a mistyped tag without blocking it", () => {
      withStage({ error_message: "Try again in {durations} or {time}." });
      expect(component.unknownTags()).toEqual(["{durations}", "{time}"]);
    });

    it("should ignore braces that could not be a tag", () => {
      withStage({ error_message: "Locked {} for a while." });
      expect(component.unknownTags()).toEqual([]);
    });

    it("should report each unknown tag once", () => {
      withStage({ error_message: "{time} and {time} again" });
      expect(component.unknownTags()).toEqual(["{time}"]);
    });

    it("should flag {duration} on a stage that has no temporary action", () => {
      // With no remaining time to substitute, the server leaves the tag as written and the user reads it
      // raw - an error rather than the advisory hint an unrecognised tag gets.
      withStage({
        error_message: "Retry in about {duration}.",
        actions: [{ action_type: "PERMANENT_LOCK_USER", action_value: null }]
      });
      expect(component.durationTagUnusable()).toBe(true);
    });

    it("should flag {duration} on a deny-only or notify-only stage", () => {
      withStage({
        error_message: "Retry in about {duration}.",
        actions: [{ action_type: "DENY", action_value: null }]
      });
      expect(component.durationTagUnusable()).toBe(true);
      withStage({
        error_message: "Retry in about {duration}.",
        actions: [{ action_type: "EMAIL_ADMIN", action_value: null }]
      });
      expect(component.durationTagUnusable()).toBe(true);
    });

    it("should accept {duration} on a temporary lock or block", () => {
      withStage({
        error_message: "Retry in about {duration}.",
        actions: [{ action_type: "LOCK_USER", action_value: null }]
      });
      expect(component.durationTagUnusable()).toBe(false);
      withStage({
        error_message: "Retry in about {duration}.",
        actions: [{ action_type: "BLOCK_IP", action_value: null }]
      });
      expect(component.durationTagUnusable()).toBe(false);
    });

    it("should not flag a message that does not use the tag", () => {
      withStage({
        error_message: "Your account has been locked.",
        actions: [{ action_type: "PERMANENT_LOCK_USER", action_value: null }]
      });
      expect(component.durationTagUnusable()).toBe(false);
    });

    it("should report the message length for the counter", () => {
      withStage({ error_message: "Locked." });
      expect(component.errorMessageLength()).toBe(7);
      withStage({ error_message: null });
      expect(component.errorMessageLength()).toBe(0);
    });
  });
});
