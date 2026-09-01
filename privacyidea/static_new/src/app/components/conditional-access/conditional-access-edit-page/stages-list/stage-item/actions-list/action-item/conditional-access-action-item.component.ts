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
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  actionValueError,
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  ConditionalAccessActionType,
  ConditionalAccessStageAction,
  ConditionalAccessTarget,
  parseActionDurationSeconds
} from "@services/conditional-access/conditional-access-policy.service";
import { SmtpService, SmtpServiceInterface } from "@services/smtp/smtp.service";
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";

// One-line explanation of what each action does, shown under the action select.
const ACTION_DESCRIPTIONS: Record<ConditionalAccessActionType, string> = {
  LOCK_USER: $localize`Temporarily lock the user out for the duration below.`,
  PERMANENT_LOCK_USER: $localize`Lock the user out until an administrator unlocks them.`,
  BLOCK_IP: $localize`Temporarily block the request's source IP for the duration below.`,
  PERMANENT_BLOCK_IP: $localize`Block the request's source IP until an administrator unblocks it.`,
  EMAIL_ADMIN: $localize`Send a notification email to an admin recipient group.`,
  EMAIL_USER: $localize`Send a notification email to the affected user.`,
  DENY: $localize`Reject the request; it clears itself as failures age out of the window.`
};

// How a given action type's action_value is edited:
// - "duration": a single integer (seconds), written as a plain number. The object form carrying
//   duration_seconds is also accepted on read, because a policy written through the API may use it.
// - "email": a JSON object with the fields listed in EMAIL_FIELDS.
// - "none": the action takes no value (stored as null).
type ActionValueMode = "duration" | "email" | "none";

// The duration is always stored and sent to the backend in seconds; the unit select only changes
// how it is entered and displayed.
type DurationUnit = "seconds" | "minutes" | "hours";

const DURATION_UNIT_FACTORS: Record<DurationUnit, number> = {
  seconds: 1,
  minutes: 60,
  hours: 3600
};

interface EmailField {
  key: string;
  label: string;
  // "smtp" is a select over the configured SMTP server identifiers fetched from the backend;
  // "select" is one over the field's own fixed options.
  kind: "text" | "textarea" | "select" | "smtp";
  options?: readonly string[];
  onlyAdmin?: boolean;
  rows?: number;
  hint?: string;
  // Renders the hint in the error colour, for a hint that reports a problem rather than explaining the field.
  hintWarn?: boolean;
}

// Shown for the identifier when it must stay a free-text input because this admin lacks the right
// to list configured servers (see emailFields).
const SMTP_TEXT_HINT = $localize`Type the name: listing the servers needs the smtpserver_read right.`;

// Order matters for layout: the three short fields come first to share one wrapping row, then the
// wide subject/body textareas flow onto their own rows.
const EMAIL_FIELDS: readonly EmailField[] = [
  {
    key: "smtp_identifier",
    label: $localize`SMTP server`,
    kind: "smtp",
    hint: $localize`The configured SMTP server that sends the email.`
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

// The {tag} substitutions available in the subject/body, matching the render context the engine
// builds (privacyidea/lib/conditional_access/engine.py).
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
  imports: [
    MatButtonModule,
    MatCheckboxModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    InfoHintComponent
  ],
  templateUrl: "./conditional-access-action-item.component.html",
  styleUrl: "./conditional-access-action-item.component.scss"
})
export class ConditionalAccessActionItemComponent {
  protected readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly smtpService: SmtpServiceInterface = inject(SmtpService);

  readonly action = input.required<ConditionalAccessStageAction>();
  readonly target = input<ConditionalAccessTarget>("user");
  readonly updateAction = output<Partial<ConditionalAccessStageAction>>();
  readonly removeAction = output<void>();

  readonly emailPlaceholders = EMAIL_PLACEHOLDERS;

  readonly actionDescription = computed<string>(() => ACTION_DESCRIPTIONS[this.action().action_type] ?? "");

  // Whether the configured SMTP servers can be listed for the identifier field: /smtpserver/ requires
  // smtpserver_read, so without it the list is never fetched (see SmtpService); the email actions stay
  // offered either way, with the identifier falling back to a free-text input carrying
  // SMTP_TEXT_HINT so the admin sees why there is nothing to pick from.
  readonly smtpServersListable = computed<boolean>(() => this.authService.actionAllowed("smtpserver_read"));

  // Action types offered for the current target (see /targets); the currently-selected type is
  // always included so a stale, now-incompatible action stays visible in the select instead of
  // being dropped on the next save.
  readonly allowedActionTypes = computed<ConditionalAccessActionType[]>(() => {
    const allowed = this.policyService.actionsForTarget(this.target());
    const current = this.action().action_type;
    return allowed.includes(current) ? allowed : [...allowed, current];
  });

  // Whether the selected action is valid for the current target; switching the target can leave a
  // stale, now-incompatible action (e.g. LOCK_USER under source_ip), flagged here so it is fixed
  // before the backend 400s, though treated as valid while the allowed list is still loading
  // (empty), since compatibility cannot yet be judged.
  readonly isActionAllowedForTarget = computed<boolean>(() => {
    const allowed = this.policyService.actionsForTarget(this.target());
    return allowed.length === 0 || allowed.includes(this.action().action_type);
  });

  // Effective checkbox state; when the action carries no explicit value, the display mirrors the
  // server's action-aware default, where the standing DENY verdict re-triggers and the
  // lock/email/block effects fire once at the threshold.
  readonly retriggerChecked = computed<boolean>(() => {
    const action = this.action();
    if (action.retrigger_above_threshold != null) {
      return action.retrigger_above_threshold;
    }
    return action.action_type === "DENY";
  });

  readonly valueMode = computed<ActionValueMode>(() =>
    ConditionalAccessActionItemComponent.modeFor(this.action().action_type)
  );

  // What is missing from this action's value, or null when the backend would accept it. Shown next to the
  // field so the admin fixes it here rather than reading a 400 after saving; the edit page gates Save on the
  // same rule (see actionValuesValid).
  readonly actionValueError = computed<string | null>(() => actionValueError(this.action()));

  readonly emailFields = computed<EmailField[]>(() => {
    const isAdmin = this.action().action_type === "EMAIL_ADMIN";
    const fields = EMAIL_FIELDS.filter((field) => isAdmin || !field.onlyAdmin);
    if (this.smtpServersListable()) {
      return fields;
    }
    // With no list to pick from, the identifier stays a plain input the admin can type a server
    // name into, and the hint explains why the configured ones are not offered.
    return fields.map((field) =>
      field.kind === "smtp" ? { ...field, kind: "text", hint: SMTP_TEXT_HINT, hintWarn: true } : field
    );
  });

  // The identifiers of the configured SMTP servers, from /smtpserver/ (see SmtpService).
  readonly smtpIdentifiers = computed<string[]>(() =>
    this.smtpService.smtpServers().map((server) => server.identifier)
  );

  // Nothing can be said about the servers while the request is in flight; since a template prefills
  // its email action expanded, without this the "none configured" hint flashes on the create page.
  readonly smtpServersLoading = computed<boolean>(() => this.smtpService.smtpServerResource.isLoading());

  // Options of the SMTP server select: the configured identifiers plus the one the action already
  // carries when not among them, so mat-select does not render a blank trigger for an option-less
  // value the admin needs to see.
  readonly smtpOptions = computed<string[]>(() => {
    const identifiers = this.smtpIdentifiers();
    const current = this.emailFieldValue("smtp_identifier");
    return current && !identifiers.includes(current) ? [...identifiers, current] : identifiers;
  });

  // Stored identifier when it names a server that is no longer configured (deleted or renamed), in
  // which case the engine finds no server and skips the email (_send_action_email), so it is
  // flagged rather than left looking valid; judged only against a non-empty list, since until
  // /smtpserver/ has answered, calling the stored one gone would be a guess.
  readonly staleSmtpIdentifier = computed<string>(() => {
    const identifiers = this.smtpIdentifiers();
    const current = this.emailFieldValue("smtp_identifier");
    return identifiers.length > 0 && !identifiers.includes(current) ? current : "";
  });

  private static modeFor(actionType: ConditionalAccessActionType): ActionValueMode {
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

  readonly durationUnit = signal<DurationUnit>("seconds");

  readonly durationUnits: readonly DurationUnit[] = ["seconds", "minutes", "hours"];

  // The raw stored duration in seconds, or null if unset/invalid. Every shape the backend accepts is read,
  // not just the bare number this editor writes, so a duration set through the API renders in the field
  // instead of looking empty.
  private durationSeconds(): number | null {
    return parseActionDurationSeconds(this.action().action_value);
  }

  // Display value in the currently selected unit.
  durationValue(): string {
    const seconds = this.durationSeconds();
    if (seconds == null) {
      return "";
    }
    return String(seconds / DURATION_UNIT_FACTORS[this.durationUnit()]);
  }

  emailFieldValue(key: string): string {
    const value = this.emailValue()[key];
    if (value == null) {
      return key === "mimetype" ? "plain" : "";
    }
    return String(value);
  }

  onActionTypeChange(actionType: ConditionalAccessActionType): void {
    // A value shaped for the previous mode is meaningless in a different one, so it resets when the
    // mode changes (e.g. switching an email object to a duration).
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
    const seconds = Number.isNaN(parsed) ? null : parsed * DURATION_UNIT_FACTORS[this.durationUnit()];
    this.updateAction.emit({ action_value: seconds });
  }

  onDurationUnitChange(unit: DurationUnit): void {
    // Keeps the entered number and re-interprets it in the new unit, matching the policy
    // time-window selector.
    const current = this.durationValue();
    this.durationUnit.set(unit);
    const parsed = parseInt(current, 10);
    if (!Number.isNaN(parsed)) {
      this.updateAction.emit({ action_value: parsed * DURATION_UNIT_FACTORS[unit] });
    }
  }

  onEmailFieldInput(key: string, value: string): void {
    const next = { ...this.emailValue() };
    // mimetype always carries a value (defaults to "plain"); other empty fields are dropped so the
    // stored object stays minimal.
    if (value === "" && key !== "mimetype") {
      delete next[key];
    } else {
      next[key] = value;
    }
    this.updateAction.emit({ action_value: Object.keys(next).length > 0 ? next : null });
  }

  onRetriggerChange(checked: boolean): void {
    this.updateAction.emit({ retrigger_above_threshold: checked });
  }

  onRemoveAction(): void {
    this.removeAction.emit();
  }
}
