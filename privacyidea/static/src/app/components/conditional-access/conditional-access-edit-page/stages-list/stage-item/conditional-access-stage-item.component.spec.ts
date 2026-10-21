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
import { applyEach, FieldTree, form } from "@angular/forms/signals";
import { AuthService } from "@services/auth/auth.service";
import {
  CA_ERR,
  ConditionalAccessStageFormModel,
  stageSchema,
  toStageFormModel
} from "@services/conditional-access/conditional-access-policy-form";
import {
  ConditionalAccessActionType,
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyStage,
  ConditionalAccessStageAction,
  ConditionalAccessTarget,
  DefaultErrorMessage
} from "@services/conditional-access/conditional-access-policy.service";
import { SmtpService } from "@services/smtp/smtp.service";
import { MockAuthService } from "@testing/mock-services/mock-auth-service";
import { MockConditionalAccessPolicyService } from "@testing/mock-services/mock-conditional-access-policy-service";
import { MockSmtpService } from "@testing/mock-services/mock-smtp-service";
import { ERR } from "@utils/form-rules.utils";
import { ConditionalAccessStageItemComponent } from "./conditional-access-stage-item.component";

// jsdom has no validity.badInput; a number input that holds text the browser cannot parse is simulated.
const rejectInputAsNumber = (input: HTMLInputElement): void => {
  Object.defineProperty(input, "validity", { configurable: true, get: () => ({ badInput: true }) });
};

describe("ConditionalAccessStageItemComponent", () => {
  let component: ConditionalAccessStageItemComponent;
  let fixture: ComponentFixture<ConditionalAccessStageItemComponent>;
  let model: WritableSignal<{ stages: ConditionalAccessStageFormModel[] }>;
  let stageFields: FieldTree<ConditionalAccessStageFormModel[]>;

  const stage: ConditionalAccessPolicyStage = {
    failure_threshold: 5,
    actions: [{ action_type: "LOCK_USER", action_value: 600 }]
  };

  // Puts a stage in the form the item is bound to, the way the policy form holds it; the stage is the one above
  // unless overridden.
  const withStage = (override: Partial<ConditionalAccessPolicyStage>) => {
    model.set({ stages: [toStageFormModel({ ...stage, ...override })] });
    fixture.componentRef.setInput("stage", stageFields[0]);
    fixture.detectChanges();
  };
  const stored = () => model().stages[0];
  const thresholdInput = (): HTMLInputElement =>
    fixture.nativeElement.querySelector("input[type=number]") as HTMLInputElement;
  const type = (input: HTMLInputElement | HTMLTextAreaElement, value: string) => {
    input.value = value;
    input.dispatchEvent(new Event("input"));
    fixture.detectChanges();
  };
  const messages = () =>
    Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll("mat-error")).map((error) =>
      error.textContent?.trim()
    );

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConditionalAccessStageItemComponent],
      providers: [
        { provide: ConditionalAccessPolicyService, useClass: MockConditionalAccessPolicyService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: SmtpService, useClass: MockSmtpService }
      ]
    }).compileComponents();

    model = signal({ stages: [toStageFormModel(stage)] });
    stageFields = TestBed.runInInjectionContext(() => form(model, (p) => applyEach(p.stages, stageSchema))).stages;
    fixture = TestBed.createComponent(ConditionalAccessStageItemComponent);
    fixture.componentRef.setInput("stage", stageFields[0]);
    fixture.componentRef.setInput("stageNumber", 1);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("failure threshold", () => {
    it("should write a typed threshold to the stage", () => {
      type(thresholdInput(), "10");
      expect(stored().failure_threshold).toBe(10);
    });

    it("should accept a threshold of 0 for an always-matching DENY stage", () => {
      withStage({ actions: [{ action_type: "DENY", action_value: null }] });
      type(thresholdInput(), "0");
      expect(stored().failure_threshold).toBe(0);
      expect(stageFields[0].failure_threshold().errors()).toEqual([]);
    });

    it("should hold an emptied threshold as missing and say what is expected once left", () => {
      type(thresholdInput(), "");
      thresholdInput().dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(stored().failure_threshold).toBeNull();
      expect(messages()).toEqual(["Enter a whole number of at least 1, or 0 on a stage carrying only DENY."]);
    });

    it("should say what is expected for text the browser cannot read as a number", () => {
      rejectInputAsNumber(thresholdInput());
      type(thresholdInput(), "abc");
      thresholdInput().dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(
        stageFields[0]
          .failure_threshold()
          .errors()
          .map((error) => error.kind)
      ).toContain(ERR.parse);
      expect(messages()).toEqual(["Enter a whole number of at least 1, or 0 on a stage carrying only DENY."]);
    });

    it("should reject a negative threshold", () => {
      type(thresholdInput(), "-1");
      thresholdInput().dispatchEvent(new Event("blur"));
      fixture.detectChanges();
      expect(
        stageFields[0]
          .failure_threshold()
          .errors()
          .map((error) => error.kind)
      ).toEqual([ERR.min]);
      expect(messages()).toHaveLength(1);
    });

    // A threshold counts failures, so the minimum is 1 unless every action on the stage is a standing
    // DENY verdict, which is what the backend's _validate_threshold_for_actions allows at 0.
    it.each([
      ["only DENY", [{ action_type: "DENY", action_value: null }], true],
      ["a counting action", [{ action_type: "LOCK_USER", action_value: 60 }], false],
      [
        "a decision plus a counting action",
        [
          { action_type: "DENY", action_value: null },
          { action_type: "LOCK_USER", action_value: 60 }
        ],
        false
      ],
      ["no actions at all", [], false]
    ])("should hint at a zero threshold only for a stage with %s", (_label, actions, allowed) => {
      withStage({ failure_threshold: 5, actions: actions as ConditionalAccessStageAction[] });
      expect(component.zeroThresholdHint()).toBe(allowed);
      expect(fixture.nativeElement.querySelector("mat-hint").textContent).toContain(
        allowed ? "0 means always" : "At least 1"
      );
    });

    it("should flag a stage already sitting at 0 once an action stops allowing it", () => {
      withStage({ failure_threshold: 0, actions: [{ action_type: "DENY", action_value: null }] });
      expect(stageFields[0].failure_threshold().errors()).toEqual([]);
      expect(messages()).toEqual([]);

      // Adding a lock to the same stage leaves the threshold at 0, which no longer holds. The threshold was never
      // focused, and the reason shows anyway.
      stageFields[0].actions().value.update((actions) => [...actions, { action_type: "LOCK_USER", action_value: 60 }]);
      fixture.detectChanges();
      expect(
        stageFields[0]
          .failure_threshold()
          .errors()
          .map((error) => error.kind)
      ).toEqual([CA_ERR.stageThreshold]);
      expect(messages()).toEqual(['A threshold of 0 means "always" and needs a stage carrying only DENY.']);
    });

    it("should not flag a threshold of 1 or more whatever the actions are", () => {
      withStage({ failure_threshold: 5, actions: [{ action_type: "LOCK_USER", action_value: 60 }] });
      expect(stageFields[0].failure_threshold().errors()).toEqual([]);
    });
  });

  it("should emit removeStage", () => {
    const spy = jest.spyOn(component.removeStage, "emit");
    component.onRemoveStage();
    expect(spy).toHaveBeenCalled();
  });

  describe("name", () => {
    const nameInput = (): HTMLInputElement =>
      fixture.nativeElement.querySelector(".ca-stage-name-field input") as HTMLInputElement;

    it("should write the name as typed and show it stripped as the title", () => {
      type(nameInput(), "  Warn user  ");
      expect(stored().name).toBe("  Warn user  ");
      expect(component.stageName()).toBe("Warn user");
    });

    it("should treat a name of spaces as no name", () => {
      type(nameInput(), "   ");
      expect(component.stageName()).toBe("");
    });

    it("should keep a saved stage's name as text until it is edited", () => {
      withStage({ id: 3, name: "Warn user" });
      expect(fixture.nativeElement.querySelector(".ca-stage-title-name").textContent.trim()).toBe("Warn user");
      expect(nameInput()).toBeNull();

      fixture.nativeElement.querySelector(".ca-stage-name-action").click();
      fixture.detectChanges();
      expect(nameInput().value).toBe("Warn user");
    });

    it("should name a saved stage without a name as unnamed", () => {
      withStage({ id: 3 });
      expect(fixture.nativeElement.querySelector(".ca-stage-title-name--empty")).toBeTruthy();
    });

    it("should stop editing the name on Enter", () => {
      withStage({ id: 3, name: "Warn user" });
      component.startEditingName();
      fixture.detectChanges();
      nameInput().dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
      fixture.detectChanges();
      expect(component.editingName()).toBe(false);
    });

    it("should toggle name editing", () => {
      expect(component.editingName()).toBe(false);
      component.startEditingName();
      expect(component.editingName()).toBe(true);
      component.stopEditingName();
      expect(component.editingName()).toBe(false);
    });
  });

  describe("error message", () => {
    // Served most severe first, the way /conditionalaccess/defaulterrormessages orders them: the composition
    // is "join the ones this stage carries", so the order is the only rule under test here. The table holds only
    // actions that describe a standing state - a restriction in force or a denial - because those are the only
    // ones a request can be told about; EMAIL_* are deliberately absent.
    const SUGGESTIONS: DefaultErrorMessage[] = [
      { action_type: "PERMANENT_LOCK_USER", message: "Your account has been locked." },
      { action_type: "PERMANENT_BLOCK_IP", message: "Your address has been blocked." },
      { action_type: "LOCK_USER", message: "Locked. Try again in about {duration}." },
      { action_type: "BLOCK_IP", message: "Blocked. Try again in about {duration}." },
      { action_type: "DENY", message: "Access has been denied." }
    ];

    // What /conditionalaccess/targets serves as each target's reporting actions: those that restrict it, plus
    // DENY. Filtered per target there, so a user policy never offers the block pair and vice versa.
    const REPORTING_BY_TARGET = {
      user: ["DENY", "LOCK_USER", "PERMANENT_LOCK_USER"],
      source_ip: ["BLOCK_IP", "DENY", "PERMANENT_BLOCK_IP"]
    } as Record<ConditionalAccessTarget, ConditionalAccessActionType[]>;

    let policyService: MockConditionalAccessPolicyService;

    const textarea = () => fixture.nativeElement.querySelector("textarea") as HTMLTextAreaElement;

    const withTarget = (target: ConditionalAccessTarget) => fixture.componentRef.setInput("target", target);

    beforeEach(() => {
      policyService = TestBed.inject(ConditionalAccessPolicyService) as unknown as MockConditionalAccessPolicyService;
      policyService.defaultErrorMessages.set(SUGGESTIONS);
      policyService.reportingActionsByTarget.set(REPORTING_BY_TARGET);
    });

    it("should write the error_message exactly as typed", () => {
      // Not trimmed here: the field is bound back to this value, so trimming would delete a space the
      // admin has just typed. validate_error_message strips it, and treats a blank message as none.
      withStage({ error_message: "" });
      type(textarea(), "  Locked.  ");
      expect(stored().error_message).toBe("  Locked.  ");
      type(textarea(), "   ");
      expect(stored().error_message).toBe("   ");
    });

    it("should be unticked for a stage with no message and ticked for one that has it", () => {
      withStage({ error_message: null });
      expect(component.hasCustomErrorMessage()).toBe(false);
      withStage({ error_message: "Locked." });
      expect(component.hasCustomErrorMessage()).toBe(true);
    });

    it("should stay enabled while the field is cleared mid-edit", () => {
      // Clearing the textarea leaves an empty message, not an absent one, so the field does not disable
      // itself out from under the admin the moment they select-all-and-delete.
      withStage({ error_message: "Locked." });
      type(textarea(), "");
      expect(stored().error_message).toBe("");
      expect(component.hasCustomErrorMessage()).toBe(true);
      expect(textarea().disabled).toBe(false);
    });

    it("should count the stage as having no wording only when the field is absent entirely", () => {
      withStage({ error_message: null });
      expect(component.hasCustomErrorMessage()).toBe(false);
      withStage({});
      expect(component.hasCustomErrorMessage()).toBe(false);
    });

    it("should render the message field always, disabled until the box is ticked", () => {
      // Always present, so ticking the box does not change the stage's shape on screen - only whether the
      // field can be typed into. mat-form-field has no disabled input, so this has to sit on the control.
      withStage({ error_message: null });
      expect(textarea()).toBeTruthy();
      expect(textarea().disabled).toBe(true);

      withStage({ error_message: "Locked." });
      expect(textarea().disabled).toBe(false);
    });

    it("should limit the message to the length the backend stores", () => {
      withStage({ error_message: "x".repeat(500) });
      expect(textarea().getAttribute("maxlength")).toBe("500");
      expect(fixture.nativeElement.textContent).toContain("500/500");
    });

    it("should fill in the suggestion when switched on", () => {
      withStage({ error_message: null, actions: [{ action_type: "LOCK_USER", action_value: null }] });
      component.toggleErrorMessage(true);
      expect(stored().error_message).toBe("Locked. Try again in about {duration}.");
    });

    it("should switch the message on and off from the checkbox", () => {
      withStage({ error_message: null, actions: [{ action_type: "LOCK_USER", action_value: null }] });
      const checkbox = () => fixture.nativeElement.querySelector("mat-checkbox input") as HTMLInputElement;

      checkbox().click();
      fixture.detectChanges();
      expect(stored().has_error_message).toBe(true);
      expect(stored().error_message).toBe("Locked. Try again in about {duration}.");
      expect(textarea().disabled).toBe(false);

      checkbox().click();
      fixture.detectChanges();
      expect(stored().has_error_message).toBe(false);
      expect(stored().error_message).toBe("");
      expect(textarea().disabled).toBe(true);
    });

    it("should leave out the timed half of a redundant pair", () => {
      // The only action the suggestion drops. A restriction is never weakened, so the permanent lock is the
      // row that ends up in force and the timed one could never be reported - the same reason the actions
      // list flags the pair as redundant. Order of configuration is irrelevant.
      withStage({
        error_message: null,
        actions: [
          { action_type: "LOCK_USER", action_value: null },
          { action_type: "PERMANENT_LOCK_USER", action_value: null }
        ]
      });
      expect(component.suggestedErrorMessage()).toBe("Your account has been locked.");
    });

    it("should join every reporting action the stage carries, in the order served", () => {
      // No rule beyond the order: one sentence per action that describes a standing state. The notification is
      // not one of them - no row records that an email went out, so nothing could ever report it.
      withStage({
        error_message: null,
        actions: [
          { action_type: "EMAIL_USER", action_value: null },
          { action_type: "DENY", action_value: null },
          { action_type: "PERMANENT_LOCK_USER", action_value: null }
        ]
      });
      expect(component.suggestedErrorMessage()).toBe("Your account has been locked. Access has been denied.");
    });

    it("should suggest nothing for a stage with no actions", () => {
      // A stage carries no actions until the admin picks one, so there is nothing to suggest and nothing to
      // reset to.
      withStage({ error_message: null, actions: [] });
      expect(component.suggestedErrorMessage()).toBeNull();
      expect(component.canResetErrorMessage()).toBe(false);
    });

    it("should suggest nothing for a notify-only stage", () => {
      // Such a stage refuses nothing, so no request is ever turned away while it applies and there is no
      // moment at which wording for it could be shown.
      withStage({ error_message: null, actions: [{ action_type: "EMAIL_ADMIN", action_value: null }] });
      expect(component.suggestedErrorMessage()).toBeNull();
      expect(component.canResetErrorMessage()).toBe(false);
    });

    it("should describe only the restriction when the stage also notifies", () => {
      // The lock is what later requests are refused by, and its row is what carries the wording; the email is
      // a one-off event that no row remembers.
      withStage({
        error_message: null,
        actions: [
          { action_type: "EMAIL_ADMIN", action_value: null },
          { action_type: "LOCK_USER", action_value: null }
        ]
      });
      expect(component.suggestedErrorMessage()).toBe("Locked. Try again in about {duration}.");
    });

    it("should clear the message when switched off", () => {
      withStage({ error_message: "Mine." });
      component.toggleErrorMessage(false);
      expect(stored().error_message).toBe("");
    });

    it("should not carry a message across the stage it was written for", () => {
      // Nothing about the message is held here, so switching on offers the suggestion for the stage the item is
      // bound to - never text belonging to a stage that was written before.
      withStage({ error_message: "Mine." });
      component.toggleErrorMessage(false);
      withStage({ error_message: null, actions: [{ action_type: "LOCK_USER", action_value: null }] });
      component.toggleErrorMessage(true);
      expect(stored().error_message).toBe("Locked. Try again in about {duration}.");
    });

    it("should switch on with an empty field when the stage has nothing to suggest", () => {
      withStage({ error_message: null, actions: [] });
      component.toggleErrorMessage(true);
      expect(stored().error_message).toBe("");
    });

    it("should replace the message with the suggestion on reset", () => {
      withStage({ error_message: "Stale wording.", actions: [{ action_type: "DENY", action_value: null }] });
      component.resetErrorMessageToSuggestion();
      expect(stored().error_message).toBe("Access has been denied.");
    });

    it("should reset the message from the button", () => {
      withStage({ error_message: "Stale wording.", actions: [{ action_type: "DENY", action_value: null }] });
      const button = fixture.nativeElement.querySelector(".ca-stage-error-message-row button") as HTMLButtonElement;
      expect(button.disabled).toBe(false);
      button.click();
      fixture.detectChanges();
      expect(stored().error_message).toBe("Access has been denied.");
      expect(button.disabled).toBe(true);
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

      const actions: ConditionalAccessStageAction[] = [{ action_type: "PERMANENT_LOCK_USER", action_value: null }];
      stageFields[0].actions().value.set(actions);
      expect(component.suggestedErrorMessage()).toBe("Your account has been locked.");
      expect(stored().error_message).toBe("Mine.");
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

    it("should flag a message on a stage that reports nothing", () => {
      // A notify-only stage refuses no request, so there is no moment at which this wording could be shown.
      withStage({
        error_message: "Your administrator has been notified.",
        actions: [{ action_type: "EMAIL_ADMIN", action_value: null }]
      });
      expect(component.messageUnreachable()).toBe(true);
    });

    it("should flag a message on a stage with no actions at all", () => {
      withStage({ error_message: "Locked.", actions: [] });
      expect(component.messageUnreachable()).toBe(true);
    });

    it("should not flag a message on a stage that restricts or denies", () => {
      // One reporting action is enough, whatever else the stage does alongside it. Asked per target, since that
      // is how the rule is served: the lock pair belongs to a user policy and the block pair to a source_ip one.
      const reporting: [ConditionalAccessTarget, ConditionalAccessActionType][] = [
        ["user", "LOCK_USER"],
        ["user", "PERMANENT_LOCK_USER"],
        ["user", "DENY"],
        ["source_ip", "BLOCK_IP"],
        ["source_ip", "PERMANENT_BLOCK_IP"],
        ["source_ip", "DENY"]
      ];
      for (const [target, action_type] of reporting) {
        withTarget(target);
        withStage({ error_message: "Locked.", actions: [{ action_type, action_value: null }] });
        expect(component.messageUnreachable()).toBe(false);
      }
      withTarget("user");
      withStage({
        error_message: "Locked.",
        actions: [
          { action_type: "EMAIL_ADMIN", action_value: null },
          { action_type: "LOCK_USER", action_value: null }
        ]
      });
      expect(component.messageUnreachable()).toBe(false);
    });

    it("should not flag a stage that carries no message to show", () => {
      // Nothing to warn about until there is wording: an empty or blank field is the silent default.
      withStage({ error_message: null, actions: [{ action_type: "EMAIL_ADMIN", action_value: null }] });
      expect(component.messageUnreachable()).toBe(false);
      withStage({ error_message: "   ", actions: [{ action_type: "EMAIL_ADMIN", action_value: null }] });
      expect(component.messageUnreachable()).toBe(false);
    });

    it("should stay silent until the target's constraints have loaded", () => {
      // An empty set is "not known yet", not "nothing can report", so it must not flag every stage on the page.
      policyService.reportingActionsByTarget.set({} as Record<ConditionalAccessTarget, ConditionalAccessActionType[]>);
      withStage({ error_message: "Locked.", actions: [{ action_type: "EMAIL_ADMIN", action_value: null }] });
      expect(component.messageUnreachable()).toBe(false);
    });

    it("should judge reachability by what the actions do, not by which have suggested wording", () => {
      // The two are separate questions, and the suggestion table is only the answer to the second: wording for a
      // notify action would be an authoring convenience, and must not make the editor believe it can be shown.
      policyService.defaultErrorMessages.set([
        ...SUGGESTIONS,
        { action_type: "EMAIL_ADMIN", message: "Your administrator has been notified." }
      ]);
      withStage({
        error_message: "Your administrator has been notified.",
        actions: [{ action_type: "EMAIL_ADMIN", action_value: null }]
      });
      expect(component.messageUnreachable()).toBe(true);

      // And the converse: an action that reports but carries no suggestion is still reachable.
      policyService.defaultErrorMessages.set([]);
      withStage({ error_message: "Locked.", actions: [{ action_type: "LOCK_USER", action_value: null }] });
      expect(component.messageUnreachable()).toBe(false);
    });

    it("should report the message length for the counter", () => {
      withStage({ error_message: "Locked." });
      expect(component.errorMessageLength()).toBe(7);
      withStage({ error_message: null });
      expect(component.errorMessageLength()).toBe(0);
    });
  });
});
