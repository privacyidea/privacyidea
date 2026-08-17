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
  LockoutPolicyStage,
  LockoutStageAction,
  LockoutTarget
} from "@services/conditional-access/conditional-access-policy.service";
import { ConditionalAccessActionsListComponent } from "./actions-list/conditional-access-actions-list.component";

// The one tag the server substitutes into a stage's error message.
const DURATION_TAG = "{duration}";

// Mirrors MAX_STAGE_ERROR_MESSAGE_LENGTH in privacyidea.lib.conditional_access.lockout_policy
// (Unicode(500) in the model). Enforced here too so the field cannot be overrun into a 400.
const MAX_ERROR_MESSAGE_LENGTH = 500;

// Anything shaped like a tag, so a typo ("{durations}") can be pointed out. Deliberately does
// not match "{}" or an empty brace pair: only a named placeholder could have been meant as a tag.
const TAG_PATTERN = /\{[A-Za-z_][A-Za-z0-9_]*\}/g;

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
    ConditionalAccessActionsListComponent,
    InfoHintComponent
  ],
  templateUrl: "./conditional-access-stage-item.component.html",
  styleUrl: "./conditional-access-stage-item.component.scss"
})
export class ConditionalAccessStageItemComponent {
  private readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);

  readonly stage = input.required<LockoutPolicyStage>();
  // 1-based trigger order (lowest threshold = Stage 1), shown as "Stage N".
  readonly stageNumber = input.required<number>();
  // The identity the policy acts on; passed down to the action editor so it can
  // offer only the action types valid for this target.
  readonly target = input<LockoutTarget>("user");
  readonly updateStage = output<Partial<LockoutPolicyStage>>();
  readonly removeStage = output<void>();

  // A saved stage (with an id) shows its name as text plus an edit button; an
  // unsaved stage has no id and stays in the name input until the policy is saved.
  readonly editingName = signal(false);

  readonly durationTag = DURATION_TAG;
  readonly maxErrorMessageLength = MAX_ERROR_MESSAGE_LENGTH;

  // One string for the reset button's tooltip and its accessible name: a sighted user hovering and a
  // screen-reader user tabbing must be told the same thing, and two literals would drift apart.
  readonly resetErrorMessageLabel = $localize`Replace with the suggested wording for this stage's actions`;

  readonly errorMessageHint = $localize`When enabled, the text you enter is shown to the user whenever authentication \
fails while this stage applies - including on later attempts, while a lock or block from it is still in force. It \
applies to this stage only; other stages stay silent unless you enable it there as well. By default the standard error \
response is sent instead, exactly as for any other failed authentication, so an attacker cannot tell that an account \
was locked or an address blocked.`;

  // Null until the admin touches the checkbox, after which their choice wins for the lifetime of this
  // component. Without that, clearing the textarea would set error_message to null and the field would
  // vanish mid-edit, since "is a message shown" is otherwise derived from the value having one.
  private readonly messageEnabledOverride = signal<boolean | null>(null);
  // What the field held when it was last switched off, so switching back on restores the admin's text
  // instead of silently replacing it with the suggestion. Session-only; never persisted.
  private readonly rememberedMessage = signal<string | null>(null);

  readonly showErrorMessage = computed(() => this.messageEnabledOverride() ?? !!this.stage().error_message);

  readonly errorMessageLength = computed(() => (this.stage().error_message ?? "").length);

  // The suggestion for this stage as it stands, composed the way the runtime actually reports: one
  // restriction (the first the stage carries - the server orders them most severe first, and only one
  // restriction is ever shown) followed by every notification it also triggers, since being emailed
  // about is a separate fact from being locked out. Null when the stage carries neither, e.g. an
  // allow-only stage, which has nothing to tell the user.
  readonly suggestedErrorMessage = computed(() => {
    const present = new Set(this.stage().actions.map((action) => action.action_type));
    const offered = this.policyService.defaultErrorMessages().filter((entry) => present.has(entry.action_type));
    const restriction = offered.find((entry) => entry.category === "restriction");
    const notifications = offered.filter((entry) => entry.category === "notification");
    const sentences = [...(restriction ? [restriction] : []), ...notifications].map((entry) => entry.message);
    return sentences.length ? sentences.join(" ") : null;
  });

  // Offer the reset only when it would change something: there is a suggestion, and it is not already
  // what the field holds.
  readonly canResetErrorMessage = computed(() => {
    const suggestion = this.suggestedErrorMessage();
    return !!suggestion && suggestion !== (this.stage().error_message ?? "");
  });

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

  onFailureThresholdInput(value: string): void {
    const parsed = parseInt(value, 10);
    // 0 is allowed: an ALLOW/DENY allowlist stage always matches at threshold 0.
    if (!isNaN(parsed) && parsed >= 0) {
      this.updateStage.emit({ failure_threshold: parsed });
    }
  }

  onErrorMessageInput(value: string): void {
    const trimmed = value.trim();
    this.updateStage.emit({ error_message: trimmed || null });
  }

  /**
   * Turn the user-facing message on or off for this stage.
   *
   * Off clears it - one field is the whole truth, so "say nothing" has to be a null message rather
   * than a second stored flag that could disagree with it. The cleared text is kept in memory so
   * switching back on restores what the admin wrote; only if there is nothing to restore does the
   * server's suggestion fill the field.
   */
  toggleErrorMessage(enabled: boolean): void {
    this.messageEnabledOverride.set(enabled);
    if (!enabled) {
      this.rememberedMessage.set(this.stage().error_message ?? null);
      this.updateStage.emit({ error_message: null });
      return;
    }
    this.updateStage.emit({ error_message: this.rememberedMessage() ?? this.suggestedErrorMessage() });
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

  onActionsChange(actions: LockoutStageAction[]): void {
    this.updateStage.emit({ actions });
  }

  onRemoveStage(): void {
    this.removeStage.emit();
  }
}
