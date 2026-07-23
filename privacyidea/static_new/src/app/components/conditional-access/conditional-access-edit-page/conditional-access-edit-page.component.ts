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
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  EMPTY_LOCKOUT_POLICY,
  LockoutPolicySaveParams,
  LockoutPolicyStage,
  LockoutTarget
} from "@services/conditional-access/conditional-access-policy.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { deepCopy } from "@utils/deep-copy.utils";
import { ConditionalAccessStagesListComponent } from "./stages-list/conditional-access-stages-list.component";

type TimeUnit = "seconds" | "minutes" | "hours";

const TIME_UNIT_FACTORS: Record<TimeUnit, number> = {
  seconds: 1,
  minutes: 60,
  hours: 3600
};

// Human-readable labels for the policy targets served by /conditionalaccess/targets.
// A target not listed here falls back to its raw value, so a newly added target still shows.
const TARGET_LABELS: Record<string, string> = {
  user: $localize`User`,
  source_ip: $localize`Source IP`
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

  // Pristine copy: the last-loaded/-saved state. Passed to hasChanges()/delete instead of the
  // constantly-mutating editPolicy, mirroring EventEditPageComponent's event/editEvent split.
  policy = signal<LockoutPolicySaveParams>(deepCopy(EMPTY_LOCKOUT_POLICY));
  // Working copy. Signal Forms wraps this directly (form() writes through to the same signal),
  // so scalar-field edits via [formField] and array/boolean edits via updateEditPolicy() both
  // mutate the one model.
  editPolicy = signal<LockoutPolicySaveParams>(deepCopy(EMPTY_LOCKOUT_POLICY));
  isNewPolicy = signal(true);

  readonly title = computed(() =>
    this.isNewPolicy() ? $localize`Create Conditional-Access Policy` : $localize`Edit Conditional-Access Policy`
  );

  // Only the "name" field goes through Signal Forms: it is a plain required/length-bounded string,
  // matching the proven pattern in enroll-motp/enroll-hotp. The numeric fields, booleans,
  // counter-type multi-select and the stages array are edited via plain signal updates (see
  // updateEditPolicy()) -- there is no codebase precedent for a numeric [formField] binding, and
  // the stages/actions arrays are handled by the array-composition pattern documented in
  // ConditionalAccessStagesListComponent, matching this codebase's existing EventEditPageComponent,
  // which uses the same fully-plain-signal approach for an equivalently nested-array feature.
  policyForm = form(this.editPolicy, (p) => {
    required(p.name);
    validate(p.name, (ctx) => (ctx.value().trim().length > 255 ? [{ kind: "maxlength" }] : []));
  });

  // The target's human label and the options for the target select (falls back to
  // the fixed enum until /targets loads, so the required field is never empty).
  readonly targetOptions = computed<LockoutTarget[]>(() => {
    const fromBackend = this.policyService.targets();
    return fromBackend.length ? fromBackend : (["user", "source_ip"] as LockoutTarget[]);
  });
  targetLabel(target: string): string {
    return TARGET_LABELS[target] ?? target;
  }

  // Info-hint help texts, kept as $localize strings in the component (like the
  // title and target labels) so all of this component's user-facing text lives in
  // one place and is extracted for translation.
  protected readonly targetHelp = $localize`What this policy counts and acts on. 'User' counts one user's failures and locks that user; 'Source IP' counts the distinct users an IP fails against and blocks that IP (password spraying). The target decides which actions a stage may use.`;
  protected readonly targetHelpAriaLabel = $localize`About target`;
  protected readonly priorityHelp = $localize`Priority decides how this policy ranks against the others: a lower number means higher precedence, so for an allow/deny decision the matching policy with the lowest priority number wins, while lock, block and email policies all run regardless of priority.`;
  protected readonly priorityHelpAriaLabel = $localize`About priority`;

  // The templates offered on the create page, and the currently picked one (its
  // description is shown as a hint). Editing an existing policy hides the picker.
  selectedTemplateKey = signal<string | null>(null);
  readonly selectedTemplateDescription = computed<string>(
    () => this.policyService.templates().find((t) => t.key === this.selectedTemplateKey())?.description ?? ""
  );

  timeWindowValid = computed(() => this.editPolicy().time_window_seconds >= 1);
  priorityValid = computed(() => this.editPolicy().priority >= 1);
  counterTypesValid = computed(() => this.editPolicy().counter_types_to_track.length > 0);
  stagesValid = computed(() => {
    const stages = this.editPolicy().stages;
    // Priority is not edited here; it is derived from the threshold on save. A
    // threshold of 0 is valid (an ALLOW/DENY allowlist stage always matches).
    return stages.length > 0 && stages.every((stage) => stage.failure_threshold >= 0);
  });
  // Every stage action must be allowed for the selected target (the backend
  // enforces the same via _ACTIONS_BY_TARGET and 400s otherwise). The action
  // select only offers compatible actions, but switching the target on an
  // existing policy can leave a stale, now-incompatible action behind.
  targetActionsValid = computed(() => {
    const allowed = this.policyService.actionsForTarget(this.editPolicy().target);
    // Until the allowed-actions list has loaded we cannot judge compatibility, so
    // don't block saving on it (the backend still enforces the rule).
    if (allowed.length === 0) {
      return true;
    }
    const allowedSet = new Set(allowed);
    return this.editPolicy().stages.every((stage) =>
      stage.actions.every((action) => allowedSet.has(action.action_type))
    );
  });
  // Only the highest-priority stage whose threshold is met ever fires, so two stages
  // sharing a threshold would leave one permanently dead; the backend rejects it too
  // (uq_lockout_stage_policy_threshold), so block it here.
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
      this.counterTypesValid() &&
      this.stagesValid() &&
      this.stageThresholdsUnique() &&
      this.targetActionsValid()
  );

  nameTouched = signal(false);
  showNameError = computed(() => this.nameTouched() && !this.policyForm().valid());
  nameTooLong = computed(() =>
    this.policyForm
      .name()
      .errors()
      .some((e) => e.kind === "maxlength")
  );

  // The time window is stored in seconds; the editor lets the user pick a coarser unit
  // and enter a plain number, which is converted to seconds on the way into editPolicy.
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
          this.policy.set(deepCopy(found));
          this.editPolicy.set(deepCopy(found));
          this.syncTimeWindowFromSeconds(found.time_window_seconds);
        }
      } else {
        this.isNewPolicy.set(true);
        this.editPolicyId = null;
        this.policy.set(deepCopy(EMPTY_LOCKOUT_POLICY));
        this.editPolicy.set(deepCopy(EMPTY_LOCKOUT_POLICY));
        this.syncTimeWindowFromSeconds(EMPTY_LOCKOUT_POLICY.time_window_seconds);
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet.
    effect(() => {
      const policies = this.policyService.policies();
      if (!this.isNewPolicy() && this.editPolicyId && !this.hasChanges()) {
        const found = policies.find((p) => String(p.id) === this.editPolicyId);
        if (found) {
          this.policy.set(deepCopy(found));
          this.editPolicy.set(deepCopy(found));
          this.syncTimeWindowFromSeconds(found.time_window_seconds);
        }
      }
    });

    this.pendingChangesService.registerHasChanges(() => this.hasChanges());
    this.pendingChangesService.registerSave(this.savePolicy.bind(this));
    this.pendingChangesService.registerValidChanges(() => this.canSave());
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

  onCounterTypesChange(counterTypes: string[]): void {
    this.updateEditPolicy({
      counter_types_to_track: counterTypes as LockoutPolicySaveParams["counter_types_to_track"]
    });
  }

  onTargetChange(target: LockoutTarget): void {
    this.updateEditPolicy({ target });
  }

  // Prefill the whole editor from a shipped template (create page only). The
  // template's policy is a ready-to-POST payload; the admin can still edit it.
  // A null key clears the prefill back to the empty policy (see clearTemplateSelection).
  applyTemplate(key: string | null): void {
    this.selectedTemplateKey.set(key);
    const template = key ? this.policyService.templates().find((t) => t.key === key) : undefined;
    const policy = template ? deepCopy(template.policy) : deepCopy(EMPTY_LOCKOUT_POLICY);
    delete policy.id;
    this.editPolicy.set(policy);
    this.syncTimeWindowFromSeconds(policy.time_window_seconds);
  }

  // The template select's clear button: drop the selected template and reset the
  // prefilled fields back to an empty policy.
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

  // Pick the coarsest unit that divides the stored seconds evenly, so a saved window shows
  // as e.g. "10 minutes" rather than "600 seconds", and set the value shown in that unit.
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
    const parsed = parseInt(value, 10);
    if (!isNaN(parsed) && parsed >= 1) {
      this.updateEditPolicy({ priority: parsed });
    }
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
    // Stage priority is not user-editable: only the highest matching threshold should
    // fire, so derive each stage's priority from its (unique) failure_threshold — a
    // higher threshold gets a higher priority and therefore wins when several match.
    const policy = this.editPolicy();
    const payload = {
      ...policy,
      stages: policy.stages.map((stage) => ({ ...stage, priority: stage.failure_threshold }))
    };
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
