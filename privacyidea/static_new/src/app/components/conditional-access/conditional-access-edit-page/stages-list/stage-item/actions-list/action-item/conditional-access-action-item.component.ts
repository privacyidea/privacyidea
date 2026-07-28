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

import { Component, computed, inject, input, output } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  LockoutActionType,
  LockoutStageAction,
  LockoutTarget
} from "@services/conditional-access/conditional-access-policy.service";

// One-line explanation of what each action does, shown under the action select.
const ACTION_DESCRIPTIONS: Record<LockoutActionType, string> = {
  LOCK_USER: $localize`Temporarily lock the user out for the duration below.`,
  PERMANENT_LOCK_USER: $localize`Lock the user out until an administrator unlocks them.`,
  BLOCK_IP: $localize`Temporarily block the request's source IP for the duration below.`,
  PERMANENT_BLOCK_IP: $localize`Block the request's source IP until an administrator unblocks it.`,
  EMAIL_ADMIN: $localize`Send a notification email to an admin recipient group.`,
  EMAIL_USER: $localize`Send a notification email to the affected user.`,
  ALLOW: $localize`Allow the request and skip any lower-priority policies.`,
  DENY: $localize`Reject the request; it clears itself as failures age out of the window.`
};

// How a given action type's action_value is edited:
// - "duration": a single integer (seconds), stored as a plain number.
// - "email": a JSON object with the fields listed in EMAIL_FIELDS.
// - "none": the action takes no value (stored as null).
type ActionValueMode = "duration" | "email" | "none";

interface EmailField {
  key: string;
  label: string;
  kind: "text" | "textarea" | "select";
  options?: readonly string[];
  onlyAdmin?: boolean;
  rows?: number;
  hint?: string;
}

// Order matters for layout: the three short fields come first so they share one
// wrapping row, then the wide subject/body textareas flow onto their own rows.
const EMAIL_FIELDS: readonly EmailField[] = [
  {
    key: "smtp_identifier",
    label: $localize`SMTP server identifier`,
    kind: "text",
    hint: $localize`Name of a configured SMTP server.`
  },
  {
    key: "recipient_group",
    label: $localize`Recipient group`,
    kind: "text",
    onlyAdmin: true,
    hint: $localize`Admin group to notify, e.g. internal_admins.`
  },
  { key: "mimetype", label: $localize`MIME type`, kind: "select", options: ["plain", "html"] },
  {
    key: "subject",
    label: $localize`Subject`,
    kind: "textarea",
    rows: 2,
    hint: $localize`Plain text with {placeholders}. See the list below.`
  },
  {
    key: "body",
    label: $localize`Body`,
    kind: "textarea",
    rows: 4,
    hint: $localize`Supports {placeholders}. See the list below.`
  }
];

// The {tag} substitutions available in the subject/body, matching the render
// context the engine builds (privacyidea/lib/conditional_access/engine.py).
export interface EmailPlaceholder {
  tag: string;
  description: string;
}

const EMAIL_PLACEHOLDERS: readonly EmailPlaceholder[] = [
  { tag: "{username}", description: $localize`Login name of the affected user` },
  { tag: "{realm}", description: $localize`Realm of the user` },
  { tag: "{resolver}", description: $localize`Resolver of the user` },
  { tag: "{client_ip}", description: $localize`IP address the request came from` },
  { tag: "{count}", description: $localize`Number of matching events in the time window` },
  { tag: "{threshold}", description: $localize`The stage's failure threshold` },
  { tag: "{event_type}", description: $localize`The tracked event type that tripped the stage` },
  { tag: "{stage_id}", description: $localize`ID of the stage that triggered` },
  { tag: "{policy}", description: $localize`Name of the policy` },
  { tag: "{time}", description: $localize`Time the policy tripped (UTC)` },
  { tag: "{email}", description: $localize`Email address of the user` },
  { tag: "{givenname}", description: $localize`Given name of the user` },
  { tag: "{surname}", description: $localize`Surname of the user` }
];

@Component({
  selector: "app-conditional-access-action-item",
  standalone: true,
  imports: [MatButtonModule, MatExpansionModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule],
  templateUrl: "./conditional-access-action-item.component.html",
  styleUrl: "./conditional-access-action-item.component.scss"
})
export class ConditionalAccessActionItemComponent {
  protected readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);

  readonly action = input.required<LockoutStageAction>();
  readonly target = input<LockoutTarget>("user");
  readonly updateAction = output<Partial<LockoutStageAction>>();
  readonly removeAction = output<void>();

  readonly emailPlaceholders = EMAIL_PLACEHOLDERS;

  readonly actionDescription = computed<string>(() => ACTION_DESCRIPTIONS[this.action().action_type] ?? "");

  // The action types offered for the current target (see the /targets endpoint).
  // The currently-selected type is always included so a stale, now-incompatible
  // action stays visible in the select for the user to change.
  readonly allowedActionTypes = computed<LockoutActionType[]>(() => {
    const allowed = this.policyService.actionsForTarget(this.target());
    const current = this.action().action_type;
    return allowed.includes(current) ? allowed : [...allowed, current];
  });

  // Whether the selected action is valid for the current target. Changing the
  // target can leave a stale, now-incompatible action (e.g. LOCK_USER after
  // switching to source_ip); flag it so it's fixed before the backend 400s. While
  // the allowed list is still loading (empty) we cannot judge, so treat as valid.
  readonly isActionAllowedForTarget = computed<boolean>(() => {
    const allowed = this.policyService.actionsForTarget(this.target());
    return allowed.length === 0 || allowed.includes(this.action().action_type);
  });

  readonly valueMode = computed<ActionValueMode>(() =>
    ConditionalAccessActionItemComponent.modeFor(this.action().action_type)
  );

  readonly emailFields = computed<EmailField[]>(() => {
    const isAdmin = this.action().action_type === "EMAIL_ADMIN";
    return EMAIL_FIELDS.filter((field) => isAdmin || !field.onlyAdmin);
  });

  private static modeFor(actionType: LockoutActionType): ActionValueMode {
    if (actionType === "LOCK_USER" || actionType === "BLOCK_IP") {
      return "duration";
    }
    if (actionType === "EMAIL_ADMIN" || actionType === "EMAIL_USER") {
      return "email";
    }
    return "none";
  }

  private emailValue(): Record<string, unknown> {
    const value = this.action().action_value;
    return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
  }

  durationValue(): string {
    const value = this.action().action_value;
    if (typeof value === "number") {
      return String(value);
    }
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const record = value as Record<string, unknown>;
      const nested = record["duration_seconds"] ?? record["duration"];
      return nested == null ? "" : String(nested);
    }
    return "";
  }

  emailFieldValue(key: string): string {
    const value = this.emailValue()[key];
    if (value == null) {
      return key === "mimetype" ? "plain" : "";
    }
    return String(value);
  }

  onActionTypeChange(actionType: LockoutActionType): void {
    // A value shaped for the old mode is meaningless in a different one, so reset
    // it when the mode changes (e.g. switching an email object to a duration).
    if (ConditionalAccessActionItemComponent.modeFor(actionType) !== this.valueMode()) {
      this.updateAction.emit({ action_type: actionType, action_value: null });
    } else {
      this.updateAction.emit({ action_type: actionType });
    }
  }

  onDurationInput(text: string): void {
    const trimmed = text.trim();
    if (!trimmed) {
      this.updateAction.emit({ action_value: null });
      return;
    }
    const parsed = parseInt(trimmed, 10);
    this.updateAction.emit({ action_value: Number.isNaN(parsed) ? null : parsed });
  }

  onEmailFieldInput(key: string, value: string): void {
    const next = { ...this.emailValue() };
    // mimetype always carries a value (defaults to "plain"); other empty fields
    // are dropped so the stored object stays minimal.
    if (value === "" && key !== "mimetype") {
      delete next[key];
    } else {
      next[key] = value;
    }
    this.updateAction.emit({ action_value: Object.keys(next).length > 0 ? next : null });
  }

  onRemoveAction(): void {
    this.removeAction.emit();
  }
}
