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

import { Component, computed, effect, inject, input, output, signal } from "@angular/core";
import { FieldTree, FormField } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatTooltipModule } from "@angular/material/tooltip";
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";
import {
  CA_ERR,
  ConditionalAccessStageFormModel,
  MAX_ERROR_MESSAGE_LENGTH,
  stageThresholdAllowed
} from "@services/conditional-access/conditional-access-policy-form";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  ConditionalAccessTarget,
  REDUNDANT_RESTRICTION_PAIRS
} from "@services/conditional-access/conditional-access-policy.service";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";
import { ConditionalAccessActionsListComponent } from "./actions-list/conditional-access-actions-list.component";
import { TooltipAriaLabelDirective } from "@components/shared/directives/tooltip-aria-label.directive";

// The one tag the server substitutes into a stage's error message.
const DURATION_TAG = "{duration}";

// Anything shaped like a tag, so a typo ("{durations}") can be pointed out. Deliberately does
// not match "{}" or an empty brace pair: only a named placeholder could have been meant as a tag.
const TAG_PATTERN = /\{[A-Za-z_][A-Za-z0-9_]*\}/g;

@Component({
  selector: "app-conditional-access-stage-item",
  standalone: true,
  imports: [
    TooltipAriaLabelDirective,
    MatButtonModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    FormField,
    ConditionalAccessActionsListComponent,
    InfoHintComponent
  ],
  templateUrl: "./conditional-access-stage-item.component.html",
  styleUrl: "./conditional-access-stage-item.component.scss"
})
export class ConditionalAccessStageItemComponent {
  private readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);

  // The fields of this stage in the policy form; the item binds its inputs to them and edits nothing else.
  readonly stage = input.required<FieldTree<ConditionalAccessStageFormModel>>();
  // 1-based trigger order (lowest threshold = Stage 1), shown as "Stage N".
  readonly stageNumber = input.required<number>();
  // The identity the policy acts on, passed down to the action editor so it can offer only the
  // action types valid for this target.
  readonly target = input<ConditionalAccessTarget>("user");
  readonly removeStage = output<void>();

  // A saved stage (with an id) shows its name as text plus an edit button; an unsaved stage has no
  // id and stays in the name input until the policy is saved.
  readonly editingName = signal(false);

  protected readonly CA_ERR = CA_ERR;
  protected readonly hasError = hasError;
  protected hasAnyError(field: FieldTree<unknown>, kinds: readonly string[]): boolean {
    return kinds.some((kind) => hasError(field, kind));
  }
  // The kinds the threshold reports for text that is not a whole number of at least 0 (or 1, see stageSchema).
  protected readonly thresholdNumberErrorKinds = [ERR.required, ERR.parse, ERR.min, CA_ERR.notInteger];

  readonly durationTag = DURATION_TAG;
  readonly maxErrorMessageLength = MAX_ERROR_MESSAGE_LENGTH;

  // One string for the reset button's tooltip and its accessible name: a sighted user hovering and a
  // screen-reader user tabbing must be told the same thing, and two literals would drift apart.
  readonly resetErrorMessageLabel = $localize`:@@conditionalAccess.replaceSuggestedWordingStage:Replace with the suggested wording for this stage's actions`;

  readonly durationTagUnusableHint = $localize`:@@conditionalAccess.durationNeedsTemporaryLock:{duration} needs a temporary lock or block to count down. This stage \
has none, so it would be shown to the user as written - remove the tag, or add a temporary action.`;

  readonly errorMessageHint = $localize`:@@conditionalAccess.shownUserRequestStage:Shown to the user on a request this stage turns away before the password \
or OTP is checked: while a lock or block written by this stage is in force, or when this stage denies access. Not \
on the request that trips the stage - that one gets the answer it had coming, and the restriction applies from the \
next request. It applies to this stage only. Left empty, the user is told only "Authentication failed.", so a \
rejection cannot be told apart from any other failed authentication - unless the \
"show_default_ca_error_message" policy is set, which fills in the default wording for this stage's actions.`;

  readonly messageUnreachableHint = $localize`:@@conditionalAccess.stageNeitherRestrictsAccess:This stage neither restricts access nor denies it, so no request is \
ever turned away while it applies and this message would never be shown. Add a lock, block or deny action, or \
leave the message empty.`;

  // Whether this stage carries wording of its own. The field itself is always rendered - disabled rather than
  // hidden, so the stage's shape does not change as the box is ticked - and this drives that disabling.
  readonly hasCustomErrorMessage = computed(() => this.stage().has_error_message().value());

  private readonly errorMessage = computed(() => this.stage().error_message().value());
  private readonly actions = computed(() => this.stage().actions().value());

  // The name as the backend keeps it: stripped, so a name of spaces is no name.
  readonly stageName = computed(() => this.stage().name().value().trim());

  readonly errorMessageLength = computed(() => this.errorMessage().length);

  // The actions whose wording a request could ever be shown: a restriction in force, or a denial. Served for
  // this target rather than listed here or inferred from the suggested wording - which answers "has a default
  // sentence", not "can report at all" - so the rule comes from the place that defines it.
  private readonly reportingActions = computed(
    () => new Set(this.policyService.reportingActionsByTarget()[this.target()] ?? [])
  );

  // The suggestion for this stage as it stands: one sentence per action it carries, in the order the server
  // serves them (most severe first). That is the same wording the runtime shows, so the editor offers what a
  // user would be told. The only thing left out is the timed half of a redundant pair, which the runtime cannot
  // show either: a restriction is never weakened, so the permanent action's row is the one in force. Null when
  // the stage carries no action the server offers wording for - a notify-only stage included, nothing being able
  // to report what it did.
  readonly suggestedErrorMessage = computed(() => {
    const present = new Set(this.actions().map((action) => action.action_type));
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
    return !!suggestion && suggestion !== this.errorMessage();
  });

  // The actions that leave a remaining time behind for {duration} to count down.
  private readonly hasTimedAction = computed(() =>
    this.actions().some((action) => action.action_type === "LOCK_USER" || action.action_type === "BLOCK_IP")
  );

  // Flagged because the tag cannot be substituted without a remaining time, so it reaches the user as
  // raw markup - visible, but not what the admin meant to write.
  readonly durationTagUnusable = computed(() => this.errorMessage().includes(DURATION_TAG) && !this.hasTimedAction());

  // Flagged because such a stage's wording has nowhere to be shown: it restricts nothing and denies nothing, so
  // no request is ever refused while it applies. Advisory like the tag warnings - the admin may be one action
  // away from giving it a voice. Silent until the target's constraints have loaded, so an empty set does not
  // flag every stage on the page.
  readonly messageUnreachable = computed(() => {
    const reporting = this.reportingActions();
    if (!reporting.size || !this.errorMessage().trim()) {
      return false;
    }
    return !this.actions().some((action) => reporting.has(action.action_type));
  });

  // Tags in the message that the server will not substitute. Purely advisory: the admin can
  // save anyway, because an unsubstituted brace expression is shown as written, which is a
  // legitimate thing to want in prose.
  readonly unknownTags = computed(() => {
    const matches = this.errorMessage().match(TAG_PATTERN) ?? [];
    return [...new Set(matches.filter((tag) => tag !== DURATION_TAG))];
  });

  constructor() {
    // A stage left at 0 once its actions stop allowing it shows the reason at once, instead of waiting for a focus the
    // threshold never received.
    effect(() => {
      const threshold = this.stage().failure_threshold;
      if (hasError(threshold, CA_ERR.stageThreshold)) {
        threshold().markAsTouched();
      }
    });
  }

  startEditingName(): void {
    this.editingName.set(true);
  }

  stopEditingName(): void {
    this.editingName.set(false);
  }

  // The hint under the threshold: only a stage carrying nothing but a standing DENY verdict may use 0, so the hint
  // says what 0 means for such a stage and names the minimum for the others. The rule itself is stageThresholdAllowed.
  readonly zeroThresholdHint = computed(() => stageThresholdAllowed({ failure_threshold: 0, actions: this.actions() }));

  /**
   * Turn the user-facing message on or off for this stage.
   *
   * Off clears it - one field is the whole truth, so "say nothing" has to be an empty, disabled field rather
   * than a second stored flag that could disagree with it. On starts from the server's suggestion, or
   * from an empty field when the stage has no action worth wording.
   *
   * Switching off therefore discards what was written. Deliberate: the reset button already puts the
   * suggestion back.
   */
  toggleErrorMessage(enabled: boolean): void {
    this.stage()
      .error_message()
      .value.set(enabled ? (this.suggestedErrorMessage() ?? "") : "");
  }

  /**
   * Replace the message with the suggestion for the stage's current actions.
   *
   * Manual by design: the actions can change long after the message was written, and regenerating on
   * every change would throw away an admin's wording without asking. This is the way to pick the new
   * suggestion up once they do want it.
   */
  resetErrorMessageToSuggestion(): void {
    this.stage()
      .error_message()
      .value.set(this.suggestedErrorMessage() ?? "");
  }

  onRemoveStage(): void {
    this.removeStage.emit();
  }
}
