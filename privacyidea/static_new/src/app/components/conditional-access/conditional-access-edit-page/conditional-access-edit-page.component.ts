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

import { Component, computed, effect, inject, OnDestroy, signal } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { form, FormField, required, validate } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatTooltipModule } from "@angular/material/tooltip";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { ErrorStateDirective } from "@components/shared/directives/error-state.directive";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  CountMode,
  EMPTY_LOCKOUT_POLICY,
  LockoutPolicy,
  LockoutPolicyCondition,
  LockoutPolicySaveParams,
  LockoutPolicyStage,
  LockoutTarget
} from "@services/conditional-access/conditional-access-policy.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { deepCopy } from "@utils/deep-copy.utils";
import { ConditionalAccessConditionsComponent } from "./conditions/conditional-access-conditions.component";
import { ConditionalAccessStagesListComponent } from "./stages-list/conditional-access-stages-list.component";

type TimeUnit = "seconds" | "minutes" | "hours";

const TIME_UNIT_FACTORS: Record<TimeUnit, number> = {
  seconds: 1,
  minutes: 60,
  hours: 3600
};

// The actions that state a standing verdict instead of reacting to a failure count. They are the only
// ones a stage may carry at threshold 0, where they then apply to every request the policy covers -
// mirroring DECISION_ACTIONS and _validate_threshold_for_actions in lib/conditional_access.
const STANDING_DECISION_ACTIONS: string[] = ["ALLOW", "DENY"];

// Human-readable labels for the policy targets served by /conditionalaccess/targets; a target missing here falls back
// to its raw value.
const TARGET_LABELS: Record<string, string> = {
  user: $localize`User`,
  source_ip: $localize`Source IP`
};

// Human-readable labels for the count modes served by /conditionalaccess/targets; a mode missing here falls back to its
// raw value.
const COUNT_MODE_LABELS: Record<string, string> = {
  PER_REQUEST: $localize`Per Request`,
  PER_ATTEMPT: $localize`Per Attempt`,
  DISTINCT_USERS: $localize`Distinct Users`
};

@Component({
  selector: "app-conditional-access-edit-page",
  standalone: true,
  imports: [
    FormField,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTooltipModule,
    ScrollToTopDirective,
    StickyHeaderDirective,
    InfoHintComponent,
    ClearButtonComponent,
    ErrorStateDirective,
    ConditionalAccessConditionsComponent,
    ConditionalAccessStagesListComponent
  ],
  templateUrl: "./conditional-access-edit-page.component.html",
  styleUrl: "./conditional-access-edit-page.component.scss"
})
export class ConditionalAccessEditPageComponent implements OnDestroy {
  protected readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private editPolicyId: string | null = null;

  // Pristine copy of the last-loaded/-saved state, kept separate from the constantly-mutating
  // editPolicy for hasChanges()/delete, mirroring EventEditPageComponent's event/editEvent split.
  policy = signal<LockoutPolicySaveParams>(deepCopy(EMPTY_LOCKOUT_POLICY));
  // Working copy that Signal Forms wraps directly (form() writes through to this signal), so both
  // [formField] scalar edits and updateEditPolicy() array/boolean edits mutate the same model.
  editPolicy = signal<LockoutPolicySaveParams>(deepCopy(EMPTY_LOCKOUT_POLICY));
  isNewPolicy = signal(true);

  readonly title = computed(() =>
    this.isNewPolicy() ? $localize`Create Conditional-Access Policy` : $localize`Edit Conditional-Access Policy`
  );

  // Only the name field goes through Signal Forms, as a plain required/length-bounded string;
  // every other field (numeric values, booleans, the counter-type multi-select, and the stages
  // array) is edited via plain signal updates in updateEditPolicy(), matching
  // EventEditPageComponent's approach for an equivalently nested-array feature.
  policyForm = form(this.editPolicy, (p) => {
    required(p.name);
    validate(p.name, (ctx) => (ctx.value().trim().length > 255 ? [{ kind: "maxlength" }] : []));
  });

  // Options for the target select, falling back to a fixed enum until /targets loads so the
  // required field is never empty.
  readonly targetOptions = computed<LockoutTarget[]>(() => {
    const fromBackend = this.policyService.targets();
    return fromBackend.length ? fromBackend : (["user", "source_ip"] as LockoutTarget[]);
  });
  targetLabel(target: string): string {
    return TARGET_LABELS[target] ?? target;
  }

  // Count modes offered for the selected target, as decided by /targets; falls back to the current
  // mode until /targets loads so the required select is never empty.
  readonly countModeOptions = computed<CountMode[]>(() => {
    const fromBackend = this.policyService.countModesForTarget(this.editPolicy().target);
    return fromBackend.length ? fromBackend : [this.editPolicy().count_mode];
  });
  countModeLabel(mode: string): string {
    return COUNT_MODE_LABELS[mode] ?? mode;
  }

  // Info-hint help text as a $localize string, keeping all of this component's user-facing text in
  // one place and extractable for translation.
  protected readonly priorityHelp = $localize`Priority decides how this policy ranks against the others: a lower number means higher precedence, so for an allow/deny decision the matching policy with the lowest priority number wins, while lock, block and email policies all run regardless of priority. It is required and must be unique across policies so the order is unambiguous.`;
  protected readonly priorityHelpAriaLabel = $localize`About priority`;

  // Templates offered on the create page and the one currently picked, whose description shows as
  // a hint; editing an existing policy hides the picker.
  selectedTemplateKey = signal<string | null>(null);
  readonly selectedTemplateDescription = computed<string>(
    () => this.policyService.templates().find((t) => t.key === this.selectedTemplateKey())?.description ?? ""
  );

  // Cached here instead of `?? []` in the template: a fresh empty array on every change-detection
  // pass marks each mat-select's view dirty, so change detection never settles and an open select
  // overlay stays parked in the top-left corner for as long as it runs.
  readonly editConditions = computed<LockoutPolicyCondition[]>(() => this.editPolicy().conditions ?? []);

  timeWindowValid = computed(() => this.editPolicy().time_window_seconds >= 1);
  // Raw text of the priority field, kept separate from the parsed value so an invalid entry is
  // reported instead of silently rewritten (see onPriorityInput).
  priorityInput = signal<string>("");
  // Priority is required with no default, so the field starts empty and the admin must
  // deliberately pick a value; anything non-integer, empty, or below 1 is invalid.
  priorityValid = computed(() => {
    const priority = this.editPolicy().priority;
    return priority != null && Number.isInteger(priority) && priority >= 1;
  });
  // Distinguishes "nothing entered yet" from "not a valid priority", so a rejected entry is
  // explained rather than just refused.
  priorityError = computed<"required" | "not-an-integer" | null>(() => {
    if (this.priorityValid()) {
      return null;
    }
    return this.priorityInput().trim() === "" ? "required" : "not-an-integer";
  });

  showPriorityError = computed(() => this.priorityError() !== null || !this.priorityUnique());
  // Priorities must be unique across policies, so the evaluation order is unambiguous and the
  // backend 400s otherwise; this surfaces the clashing policy for the inline error, excluding the
  // policy's own id so an unchanged priority is not a self-collision.
  priorityConflict = computed<LockoutPolicy | undefined>(() => {
    const priority = this.editPolicy().priority;
    if (priority == null) {
      return undefined;
    }
    const currentId = this.editPolicy().id;
    return this.policyService.policies().find((policy) => policy.priority === priority && policy.id !== currentId);
  });
  priorityUnique = computed(() => !this.priorityConflict());
  counterTypesValid = computed(() => this.editPolicy().counter_types_to_track.length > 0);
  stagesValid = computed(() => {
    const stages = this.editPolicy().stages;
    // A threshold counts failures, so it starts at 1. The exception the backend also makes
    // (_validate_threshold_for_actions): a stage whose every action is a standing ALLOW/DENY verdict
    // may use 0, which then means "always" - the allowlist and the lockdown idiom.
    return (
      stages.length > 0 &&
      stages.every(
        (stage) =>
          stage.failure_threshold >= 1 ||
          (stage.failure_threshold === 0 &&
            stage.actions.length > 0 &&
            stage.actions.every((action) => STANDING_DECISION_ACTIONS.includes(action.action_type)))
      )
    );
  });
  // Every stage action must be allowed for the selected target, matching the backend's
  // _ACTIONS_BY_TARGET check; the action select only offers compatible actions, but switching an
  // existing policy's target can leave a stale, now-incompatible action behind.
  targetActionsValid = computed(() => {
    const allowed = this.policyService.actionsForTarget(this.editPolicy().target);
    // Until the allowed-actions list has loaded, compatibility cannot be judged, so saving is not
    // blocked on it; the backend still enforces the rule.
    if (allowed.length === 0) {
      return true;
    }
    const allowedSet = new Set(allowed);
    return this.editPolicy().stages.every((stage) =>
      stage.actions.every((action) => allowedSet.has(action.action_type))
    );
  });
  // The count mode must be one the selected target supports, matching the backend's
  // _COUNT_MODES_BY_TARGET check; switching an existing policy's target can leave a stale,
  // now-incompatible mode behind, surfaced as a validation error rather than silently rewritten,
  // mirroring targetActionsValid.
  countModeValid = computed(() => {
    const allowed = this.policyService.countModesForTarget(this.editPolicy().target);
    // Until the supported-modes list has loaded, compatibility cannot be judged, so saving is not
    // blocked on it; the backend still enforces the rule.
    if (allowed.length === 0) {
      return true;
    }
    return allowed.includes(this.editPolicy().count_mode);
  });
  // Every condition value must still be one the backend accepts (_validate_condition_value rejects
  // values outside the type's current vocabulary); since the editor PATCHes the whole policy, a stale
  // value like a deleted realm would 400 on any save, so this surfaces why, mirroring countModeValid
  // and targetActionsValid.
  readonly staleConditionValues = computed(() => this.policyService.staleConditionValues(this.editPolicy().conditions));
  conditionValuesValid = computed(() => this.staleConditionValues().length === 0);
  // Only the highest matching threshold ever fires, so two stages sharing a threshold would leave
  // one permanently dead; the backend also rejects this (uq_lockout_stage_policy_threshold), so it
  // is blocked here too.
  stageThresholdsUnique = computed(() => {
    const thresholds = this.editPolicy().stages.map((stage) => stage.failure_threshold);
    return new Set(thresholds).size === thresholds.length;
  });

  hasChanges = computed(() => JSON.stringify(this.policy()) !== JSON.stringify(this.editPolicy()));
  canSave = computed(
    () =>
      this.policyForm().valid() &&
      this.timeWindowValid() &&
      this.priorityValid() &&
      this.priorityUnique() &&
      this.counterTypesValid() &&
      this.stagesValid() &&
      this.stageThresholdsUnique() &&
      this.targetActionsValid() &&
      this.countModeValid() &&
      this.conditionValuesValid()
  );

  nameTouched = signal(false);
  showNameError = computed(() => this.nameTouched() && !this.policyForm().valid());
  nameTooLong = computed(() =>
    this.policyForm
      .name()
      .errors()
      .some((e) => e.kind === "maxlength")
  );

  // The time window is stored in seconds; the editor lets the admin pick a coarser unit and enter a
  // plain number, converted to seconds on the way into editPolicy.
  timeWindowUnit = signal<TimeUnit>("seconds");
  timeWindowValue = signal<number>(EMPTY_LOCKOUT_POLICY.time_window_seconds);

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const id = params.get("id");
      if (id) {
        this.isNewPolicy.set(false);
        this.editPolicyId = id;
        const found = this.policyService.policies().find((p) => String(p.id) === id);
        if (found) {
          this.loadPolicy(found);
        }
      } else {
        this.isNewPolicy.set(true);
        this.editPolicyId = null;
        this.loadPolicy(EMPTY_LOCKOUT_POLICY);
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const policies = this.policyService.policies();
      if (!this.isNewPolicy() && this.editPolicyId && !this.hasChanges()) {
        const found = policies.find((p) => String(p.id) === this.editPolicyId);
        if (found) {
          this.loadPolicy(found);
        }
      }
    });

    this.pendingChangesService.registerHasChanges(() => this.hasChanges());
    this.pendingChangesService.registerSave(this.savePolicy.bind(this));
    this.pendingChangesService.registerValidChanges(() => this.canSave());
  }

  // Seeds both the pristine and working copies from one policy, each its own deep copy, so editing
  // one cannot reach into the other.
  private loadPolicy(policy: LockoutPolicySaveParams): void {
    const loaded = deepCopy(policy);
    // The read endpoint spells "no conditions" as an empty list, while this editor's model omits the
    // key entirely; collapsing the two here keeps hasChanges()'s JSON diff from reporting a change
    // over that spelling alone.
    if (!loaded.conditions?.length) {
      delete loaded.conditions;
    }
    this.policy.set(loaded);
    this.editPolicy.set(deepCopy(loaded));
    this.syncTimeWindowFromSeconds(loaded.time_window_seconds);
    this.syncPriorityInput(loaded.priority);
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  updateEditPolicy(partial: Partial<LockoutPolicySaveParams>): void {
    this.editPolicy.set({ ...this.editPolicy(), ...partial });
  }

  onStagesChange(stages: LockoutPolicyStage[]): void {
    this.updateEditPolicy({ stages });
  }

  // No conditions means the absence of the key, not an empty list, so adding and removing a
  // condition again does not register as a change.
  onConditionsChange(conditions: LockoutPolicyCondition[]): void {
    this.updateEditPolicy({ conditions: conditions.length ? conditions : undefined });
  }

  onCounterTypesChange(counterTypes: string[]): void {
    this.updateEditPolicy({
      counter_types_to_track: counterTypes as LockoutPolicySaveParams["counter_types_to_track"]
    });
  }

  onTargetChange(target: LockoutTarget): void {
    // Only the target changes here; the count mode is left as-is, so switching to a target that does
    // not support it (e.g. DISTINCT_USERS under a user target) surfaces as a countModeValid error
    // that blocks saving instead of being silently rewritten, mirroring targetActionsValid.
    this.updateEditPolicy({ target });
  }

  onCountModeChange(count_mode: CountMode): void {
    this.updateEditPolicy({ count_mode });
  }

  // Prefills the whole editor from a shipped template on the create page with a ready-to-POST
  // payload the admin can still edit; a null key clears the prefill back to the empty policy (see
  // clearTemplateSelection).
  applyTemplate(key: string | null): void {
    this.selectedTemplateKey.set(key);
    const template = key ? this.policyService.templates().find((t) => t.key === key) : undefined;
    const prefill = template ? deepCopy(template.policy) : deepCopy(EMPTY_LOCKOUT_POLICY);
    delete prefill.id;
    // Templates carry no priority, since the admin must pick a unique one, so the missing key is
    // normalized to null leaving the field empty (see priorityValid); spelling out the target type
    // here makes the compiler enforce that normalization.
    const policy: LockoutPolicySaveParams = {
      ...prefill,
      priority: prefill.priority ?? null,
      stages: prefill.stages
    };
    this.editPolicy.set(policy);
    this.syncTimeWindowFromSeconds(policy.time_window_seconds);
    this.syncPriorityInput(policy.priority);
  }

  // The template select's clear button: drops the selected template and resets the prefilled
  // fields back to an empty policy.
  clearTemplateSelection(): void {
    this.applyTemplate(null);
  }

  onTimeWindowInput(value: string): void {
    const parsed = parseInt(value, 10);
    if (!isNaN(parsed) && parsed >= 1) {
      this.timeWindowValue.set(parsed);
      this.updateEditPolicy({ time_window_seconds: parsed * TIME_UNIT_FACTORS[this.timeWindowUnit()] });
    }
  }

  onTimeWindowUnitChange(unit: TimeUnit): void {
    this.timeWindowUnit.set(unit);
    this.updateEditPolicy({ time_window_seconds: this.timeWindowValue() * TIME_UNIT_FACTORS[unit] });
  }

  // Picks the coarsest unit that divides the stored seconds evenly, so a saved window shows as
  // e.g. "10 minutes" rather than "600 seconds", and sets the displayed value in that unit.
  private syncTimeWindowFromSeconds(seconds: number): void {
    let unit: TimeUnit = "seconds";
    if (seconds % TIME_UNIT_FACTORS.hours === 0) {
      unit = "hours";
    } else if (seconds % TIME_UNIT_FACTORS.minutes === 0) {
      unit = "minutes";
    }
    this.timeWindowUnit.set(unit);
    this.timeWindowValue.set(seconds / TIME_UNIT_FACTORS[unit]);
  }

  onPriorityInput(value: string): void {
    // Keeps the raw text and parsed value separate so a rejected entry like "1.5" stays visible
    // with its error instead of being blanked; an entry that is not a whole number >= 1 leaves
    // priority null, disabling Save and showing priorityError, and Number() (not parseInt) keeps
    // "1.5" invalid instead of truncating it to 1.
    this.priorityInput.set(value);
    const trimmed = value.trim();
    const parsed = trimmed === "" ? NaN : Number(trimmed);
    this.updateEditPolicy({ priority: Number.isInteger(parsed) ? parsed : null });
  }

  // Show the stored priority in the field (edit mode, template prefill, reset).
  private syncPriorityInput(priority: number | null): void {
    this.priorityInput.set(priority == null ? "" : String(priority));
  }

  toggleEnabled(checked: boolean): void {
    this.updateEditPolicy({ enabled: checked });
    const id = this.editPolicy().id;
    if (id != null) {
      if (checked) {
        this.policyService.enablePolicy(id);
      } else {
        this.policyService.disablePolicy(id);
      }
    }
  }

  toggleDryRun(checked: boolean): void {
    this.updateEditPolicy({ dry_run: checked });
  }

  cancelEdit(): void {
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS);
  }

  savePolicy(): Promise<boolean> {
    // Stages carry no priority: the engine evaluates them by descending failure_threshold, so the
    // thresholds the admin entered are the order.
    const policy = this.editPolicy();
    const payload: LockoutPolicySaveParams = { ...policy };
    if (!payload.conditions?.length) {
      // The backend only replaces conditions when the key is present, so an empty list is sent to
      // clear stored conditions, while a policy with none omits the key entirely — otherwise
      // removing the last condition would silently not save.
      if (this.policy().conditions?.length) {
        payload.conditions = [];
      } else {
        delete payload.conditions;
      }
    }
    return new Promise((resolve) => {
      this.policyService.savePolicy(payload).then((id) => {
        if (id !== undefined) {
          this.pendingChangesService.clearAllRegistrations();
          this.router.navigateByUrl(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS);
          resolve(true);
        } else {
          resolve(false);
        }
      });
    });
  }

  async deletePolicy(): Promise<void> {
    const id = this.policy().id;
    if (this.isNewPolicy() || id == null) {
      return;
    }
    await this.policyService.deleteWithConfirmDialog({ id, name: this.policy().name });
    this.pendingChangesService.clearAllRegistrations();
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS);
  }
}
