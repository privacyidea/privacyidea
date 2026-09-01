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

import { Component, computed, inject, input, output, signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatTooltipModule } from "@angular/material/tooltip";
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  ConditionalAccessPolicyStage,
  ConditionalAccessStageAction,
  ConditionalAccessTarget,
  REDUNDANT_RESTRICTION_PAIRS
} from "@services/conditional-access/conditional-access-policy.service";
import { ErrorStateDirective } from "@components/shared/directives/error-state.directive";
import { ConditionalAccessActionsListComponent } from "./actions-list/conditional-access-actions-list.component";

// The one tag the server substitutes into a stage's error message.
const DURATION_TAG = "{duration}";

// Mirrors MAX_ERROR_MESSAGE_LENGTH in privacyidea.lib.conditional_access.lockout_policy
// (Unicode(500) in the model). Enforced here too so the field cannot be overrun into a 400.
const MAX_ERROR_MESSAGE_LENGTH = 500;

// Anything shaped like a tag, so a typo ("{durations}") can be pointed out. Deliberately does
// not match "{}" or an empty brace pair: only a named placeholder could have been meant as a tag.
const TAG_PATTERN = /\{[A-Za-z_][A-Za-z0-9_]*\}/g;

// The actions that state a standing verdict instead of reacting to a failure count. Only a stage
// carrying nothing but these may use threshold 0, mirroring _validate_threshold_for_actions in
// lib/conditional_access/policy.py.
const STANDING_DECISION_ACTIONS: string[] = ["DENY"];

@Component({
  selector: "app-conditional-access-stage-item",
  standalone: true,
  imports: [
    MatButtonModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    ErrorStateDirective,
    ConditionalAccessActionsListComponent,
    InfoHintComponent
  ],
  templateUrl: "./conditional-access-stage-item.component.html",
  styleUrl: "./conditional-access-stage-item.component.scss"
})
export class ConditionalAccessStageItemComponent {
  private readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);

  readonly stage = input.required<ConditionalAccessPolicyStage>();
  // 1-based trigger order (lowest threshold = Stage 1), shown as "Stage N".
  readonly stageNumber = input.required<number>();
  // The identity the policy acts on, passed down to the action editor so it can offer only the
  // action types valid for this target.
  readonly target = input<ConditionalAccessTarget>("user");
  readonly updateStage = output<Partial<ConditionalAccessPolicyStage>>();
  readonly removeStage = output<void>();

  // A saved stage (with an id) shows its name as text plus an edit button; an unsaved stage has no
  // id and stays in the name input until the policy is saved.
  readonly editingName = signal(false);

  readonly durationTag = DURATION_TAG;
  readonly maxErrorMessageLength = MAX_ERROR_MESSAGE_LENGTH;

  // One string for the reset button's tooltip and its accessible name: a sighted user hovering and a
  // screen-reader user tabbing must be told the same thing, and two literals would drift apart.
  readonly resetErrorMessageLabel = $localize`Replace with the suggested wording for this stage's actions`;

  readonly durationTagUnusableHint = $localize`{duration} needs a temporary lock or block to count down. This stage \
has none, so it would be shown to the user as written - remove the tag, or add a temporary action.`;

  readonly errorMessageHint = $localize`Shown to the user when authentication fails while this stage applies, \
including on later attempts while a lock or block from it is still in force. It applies to this stage only. Left \
empty, the user is told only "Authentication failed.", so a rejection cannot be told apart from any other failed \
authentication - unless the "show_default_ca_error_message" policy is set, which fills in the default wording for this \
stage's actions.`;

  // Whether this stage carries wording of its own: absent or null means the admin has not turned it on, an
  // empty string means turned on but not written yet. The field itself is always rendered - disabled rather
  // than hidden, so the stage's shape does not change as the box is ticked - and this drives that disabling.
  // Read off the stage rather than kept in a signal here, because the stages list tracks by $index and reuses
  // this component for a different stage when one is removed: local state would outlive the stage it belongs
  // to and describe the next one.
  readonly hasCustomErrorMessage = computed(
    () => this.stage().error_message !== null && this.stage().error_message !== undefined
  );

  readonly errorMessageLength = computed(() => (this.stage().error_message ?? "").length);

  // The suggestion for this stage as it stands: one sentence per action it carries, in the order the server
  // serves them (most severe first). That is the same concatenation the runtime performs, so the wording the
  // editor offers is the wording a user would be shown - being emailed about is a separate fact from being
  // locked out, and both are said. The only thing left out is the timed half of a redundant pair, which the
  // runtime cannot show either: a restriction is never weakened, so the permanent action's row is the one in
  // force. Null when the stage carries no action the server offers wording for.
  readonly suggestedErrorMessage = computed(() => {
    const present = new Set(this.stage().actions.map((action) => action.action_type));
    const superseded = new Set(
      REDUNDANT_RESTRICTION_PAIRS.filter(([, permanent]) => present.has(permanent)).map(([timed]) => timed)
    );
    const sentences = this.policyService
      .defaultErrorMessages()
      .filter((entry) => present.has(entry.action_type) && !superseded.has(entry.action_type))
      .map((entry) => entry.message);
    return sentences.length ? sentences.join(" ") : null;
  });

  // Offer the reset only when it would change something: there is a suggestion, and it is not already
  // what the field holds.
  readonly canResetErrorMessage = computed(() => {
    const suggestion = this.suggestedErrorMessage();
    return !!suggestion && suggestion !== (this.stage().error_message ?? "");
  });

  // The actions that leave a remaining time behind for {duration} to count down.
  private readonly hasTimedAction = computed(() =>
    this.stage().actions.some((action) => action.action_type === "LOCK_USER" || action.action_type === "BLOCK_IP")
  );

  // Flagged because the tag cannot be substituted without a remaining time, so it reaches the user as
  // raw markup - visible, but not what the admin meant to write.
  readonly durationTagUnusable = computed(
    () => (this.stage().error_message ?? "").includes(DURATION_TAG) && !this.hasTimedAction()
  );

  // Tags in the message that the server will not substitute. Purely advisory: the admin can
  // save anyway, because an unsubstituted brace expression is shown as written, which is a
  // legitimate thing to want in prose.
  readonly unknownTags = computed(() => {
    const matches = (this.stage().error_message ?? "").match(TAG_PATTERN) ?? [];
    return [...new Set(matches.filter((tag) => tag !== DURATION_TAG))];
  });

  onNameInput(value: string): void {
    const trimmed = value.trim();
    this.updateStage.emit({ name: trimmed || null });
  }

  startEditingName(): void {
    this.editingName.set(true);
  }

  stopEditingName(): void {
    this.editingName.set(false);
  }

  // A threshold counts failures, so it starts at 1. Threshold 0 means "always", which only makes
  // sense for a stage whose every action is a standing DENY verdict - anything reacting to a
  // count would fire at zero failures. The backend enforces the same rule, so the minimum moves with
  // the actions the admin has picked rather than letting the save fail later.
  readonly zeroThresholdAllowed = computed(() => {
    const actions = this.stage().actions;
    return actions.length > 0 && actions.every((action) => STANDING_DECISION_ACTIONS.includes(action.action_type));
  });
  readonly minThreshold = computed(() => (this.zeroThresholdAllowed() ? 0 : 1));
  // True when the stage sits at 0 with actions that do not permit it - typically because an action
  // was added to, or changed on, an existing DENY stage.
  readonly zeroThresholdInvalid = computed(() => this.stage().failure_threshold === 0 && !this.zeroThresholdAllowed());

  onFailureThresholdInput(value: string): void {
    const parsed = parseInt(value, 10);
    // 0 is allowed: an all-DENY lockdown stage always matches at threshold 0.
    if (!isNaN(parsed) && parsed >= 0) {
      this.updateStage.emit({ failure_threshold: parsed });
    }
  }

  onErrorMessageInput(value: string): void {
    // Kept verbatim, empty string included: that is what holds the field open while the admin clears it,
    // and the server normalises a blank message to null when the policy is saved.
    this.updateStage.emit({ error_message: value });
  }

  /**
   * Turn the user-facing message on or off for this stage.
   *
   * Off clears it - one field is the whole truth, so "say nothing" has to be a null message rather
   * than a second stored flag that could disagree with it. On starts from the server's suggestion, or
   * from an empty field when the stage has no action worth wording.
   *
   * Switching off therefore discards what was written. Deliberate: remembering it would mean state that
   * belongs to this stage living in a component the list reuses for another one, and the reset button
   * already puts the suggestion back.
   */
  toggleErrorMessage(enabled: boolean): void {
    this.updateStage.emit({ error_message: enabled ? (this.suggestedErrorMessage() ?? "") : null });
  }

  /**
   * Replace the message with the suggestion for the stage's current actions.
   *
   * Manual by design: the actions can change long after the message was written, and regenerating on
   * every change would throw away an admin's wording without asking. This is the way to pick the new
   * suggestion up once they do want it.
   */
  resetErrorMessageToSuggestion(): void {
    this.updateStage.emit({ error_message: this.suggestedErrorMessage() });
  }

  onActionsChange(actions: ConditionalAccessStageAction[]): void {
    this.updateStage.emit({ actions });
  }

  onRemoveStage(): void {
    this.removeStage.emit();
  }
}
