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

import { DatePipe } from "@angular/common";
import { Component, computed, effect, inject, OnDestroy, signal, untracked } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { apply, applyEach, disabled, FieldTree, form, FormField, validate } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatProgressSpinner } from "@angular/material/progress-spinner";
import { MatSelectModule } from "@angular/material/select";
import { MatSlideToggle, MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatTooltipModule } from "@angular/material/tooltip";
import { ActivatedRoute, Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { InfoHintComponent } from "@components/shared/info-hint/info-hint.component";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  applyActionRules,
  CA_ERR,
  ConditionalAccessPolicyFormModel,
  MAX_POLICY_NAME_LENGTH,
  requiredPositiveWholeNumber,
  stageSchema,
  toPolicyFormModel,
  toPolicySaveParams
} from "@services/conditional-access/conditional-access-policy-form";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  CountMode,
  EMPTY_CONDITIONAL_ACCESS_POLICY,
  ConditionalAccessPolicy,
  ConditionalAccessPolicyCondition,
  ConditionalAccessPolicySaveParams,
  ConditionalAccessTarget
} from "@services/conditional-access/conditional-access-policy.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { normalizeDateTimeString } from "@utils/date-format.utils";
import { deepCopy } from "@utils/deep-copy.utils";
import { ERR, markRequired, requiredNonBlank, requiredNonEmptyArray } from "@utils/form-rules.utils";
import { hasError, touchAll } from "@utils/form-state.utils";
import { ConditionalAccessConditionsComponent } from "./conditions/conditional-access-conditions.component";
import { ConditionalAccessStagesListComponent } from "./stages-list/conditional-access-stages-list.component";
import {
  ConditionalAccessDryRunOffDialogComponent,
  ConditionalAccessDryRunOffDialogData,
  ConditionalAccessDryRunOffDialogResult
} from "../conditional-access-dry-run-off-dialog/conditional-access-dry-run-off-dialog.component";

// Key of the navigation state that hands the copy of a policy from its edit page to the create page.
const COPY_DRAFT_STATE_KEY = "copyOf";

// Human-readable labels for the policy targets served by /conditionalaccess/targets; a target missing here falls back
// to its raw value.
const TARGET_LABELS: Record<string, string> = {
  user: $localize`:@@common.user:User`,
  source_ip: $localize`:@@common.sourceIp:Source IP`
};

// Human-readable labels for the count modes served by /conditionalaccess/targets; a mode missing here falls back to its
// raw value.
const COUNT_MODE_LABELS: Record<string, string> = {
  PER_REQUEST: $localize`:@@conditionalAccess.perRequest:Per Request`,
  PER_ATTEMPT: $localize`:@@conditionalAccess.perAttempt:Per Attempt`,
  DISTINCT_USERS: $localize`:@@conditionalAccess.distinctUsers:Distinct Users`
};

@Component({
  selector: "app-conditional-access-edit-page",
  standalone: true,
  imports: [
    DatePipe,
    FormField,
    MatButtonModule,
    MatCheckboxModule,
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
    ConditionalAccessConditionsComponent,
    ConditionalAccessStagesListComponent,
    MatProgressSpinner
  ],
  templateUrl: "./conditional-access-edit-page.component.html",
  styleUrl: "./conditional-access-edit-page.component.scss"
})
export class ConditionalAccessEditPageComponent implements OnDestroy {
  protected readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly pendingChangesService = inject(PendingChangesService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private editPolicyId: string | null = null;

  protected readonly ERR = ERR;
  protected readonly CA_ERR = CA_ERR;
  protected readonly hasError = hasError;

  // Pristine copy of the last-loaded/-saved state, as the payload the working copy maps to. It stays separate from
  // the form model for hasChanges()/delete, mirroring EventEditPageComponent's event/editEvent split.
  policy = signal<ConditionalAccessPolicySaveParams>(deepCopy(EMPTY_CONDITIONAL_ACCESS_POLICY));
  // The form model the fields bind to. Handler edits (conditions, the toggles) go through updateModel() and the
  // stage editor writes through the stage fields it is given, so every kind of edit writes the same model.
  protected readonly policyModel = signal<ConditionalAccessPolicyFormModel>(
    toPolicyFormModel(EMPTY_CONDITIONAL_ACCESS_POLICY)
  );
  // Working copy in the shape of the stored policy, mapped from the form model.
  readonly editPolicy = computed<ConditionalAccessPolicySaveParams>(() => toPolicySaveParams(this.policyModel()));
  isNewPolicy = signal(true);
  // True only while editing an existing policy whose data hasn't arrived yet: a new policy has
  // nothing to wait for, and once policiesResource resolves once, a later reload (e.g. after
  // another admin's change) must not blank the form the user is looking at.
  protected readonly showInitialLoading = computed(
    () =>
      !this.isNewPolicy() &&
      this.policyService.policiesResource.isLoading() &&
      !this.policyService.policiesResource.hasValue()
  );

  readonly title = computed(() =>
    this.isNewPolicy()
      ? $localize`:@@conditionalAccess.createConditionalAccessPolicy:Create Conditional-Access Policy`
      : $localize`:@@conditionalAccess.editConditionalAccessPolicy:Edit Conditional-Access Policy`
  );

  // Every rule of the editor lives here, so canSave and the list of blockers read one source. Until /targets and the
  // other served lists have loaded, the rules that compare against them cannot judge and let the value pass; the
  // backend enforces them either way.
  policyForm = form(this.policyModel, (p) => {
    requiredNonBlank(p.name);
    // The backend strips the name, so the length that counts is the trimmed one.
    validate(p.name, (ctx) => (ctx.value().trim().length > MAX_POLICY_NAME_LENGTH ? [{ kind: ERR.maxLength }] : []));
    validate(p.name, () => (this.nameConflict() ? [{ kind: ERR.nameTaken }] : []));

    requiredPositiveWholeNumber(p.time_window_value);

    // Priority is required with no default, so the field starts empty and the admin must deliberately pick a value.
    requiredPositiveWholeNumber(p.priority);
    validate(p.priority, () => (this.priorityConflict() ? [{ kind: CA_ERR.priorityTaken }] : []));

    // Tracked event types are required and have no default: a policy that counts nothing would never trip, so the
    // backend rejects an empty list too.
    requiredNonEmptyArray(p.counter_types_to_track);

    // The count mode must be one the selected target supports, matching the backend's _COUNT_MODES_BY_TARGET check;
    // switching an existing policy's target can leave a stale, now-incompatible mode behind, surfaced as an error
    // rather than silently rewritten.
    markRequired(p.count_mode);
    validate(p.count_mode, (ctx) => {
      if (!ctx.value()) {
        return [{ kind: ERR.required }];
      }
      const allowed = this.policyService.countModesForTarget(ctx.valueOf(p.target));
      return allowed.length === 0 || allowed.includes(ctx.value()) ? [] : [{ kind: CA_ERR.countModeNotAllowed }];
    });

    // Only a user policy resets on a successful login: a source-IP policy aggregates a signal across accounts, where
    // one account's legitimate login must not clear it, and the backend rejects the flag on that target. The checkbox
    // is therefore shown but disabled there rather than disappearing when the target changes.
    disabled(p.reset_on_success, (ctx) => ctx.valueOf(p.target) !== "user");

    // Stages need at least one entry. The rules of one stage (the failure threshold and the specific error message)
    // are in stageSchema; the engine evaluates by descending failure_threshold, so a threshold of 0 is reserved for a
    // stage carrying only a standing verdict (see stageThresholdAllowed).
    validate(p.stages, (ctx) => (ctx.value().length > 0 ? [] : [{ kind: ERR.required }]));
    // Only the highest matching threshold ever fires, so two stages sharing a threshold would leave one permanently
    // dead; the backend also rejects this (uq_ca_stage_policy_threshold).
    validate(p.stages, (ctx) => {
      const thresholds = ctx
        .value()
        .flatMap((stage) => (stage.failure_threshold === null ? [] : [stage.failure_threshold]));
      return new Set(thresholds).size === thresholds.length ? [] : [{ kind: CA_ERR.stageThresholdDuplicate }];
    });
    applyEach(p.stages, (stage) => {
      apply(stage, stageSchema);
      applyActionRules(stage.actions, p.target, this.policyService);
    });

    // Every condition value must still be one the backend accepts (_validate_condition_value rejects values outside
    // the type's current vocabulary); since the editor PATCHes the whole policy, a stale value like a deleted realm
    // would 400 on any save.
    validate(p.conditions, (ctx) =>
      this.policyService.staleConditionValues(ctx.value()).length === 0 ? [] : [{ kind: CA_ERR.staleConditionValue }]
    );
  });

  // Options for the target select, falling back to a fixed enum until /targets loads so the
  // required field is never empty.
  readonly targetOptions = computed<ConditionalAccessTarget[]>(() => {
    const fromBackend = this.policyService.targets();
    return fromBackend.length ? fromBackend : (["user", "source_ip"] as ConditionalAccessTarget[]);
  });
  targetLabel(target: string): string {
    return TARGET_LABELS[target] ?? target;
  }

  // Count modes offered for the selected target, as decided by /targets; falls back to the current
  // mode until /targets loads so the required select is never empty.
  readonly countModeOptions = computed<CountMode[]>(() => {
    const fromBackend = this.policyService.countModesForTarget(this.policyModel().target);
    return fromBackend.length ? fromBackend : [this.policyModel().count_mode];
  });
  countModeLabel(mode: string): string {
    return COUNT_MODE_LABELS[mode] ?? mode;
  }

  // Info-hint help text as a $localize string, keeping all of this component's user-facing text in
  // one place and extractable for translation.
  protected readonly priorityHelp = $localize`:@@conditionalAccess.uniqueOrderAcrossPolicies:Unique order across policies, lowest first.`;
  protected readonly priorityHelpAriaLabel = $localize`:@@conditionalAccess.aboutPriority:About priority`;

  // Templates offered on the create page and the one currently picked, whose description shows as
  // a hint; editing an existing policy hides the picker.
  selectedTemplateKey = signal<string | null>(null);
  readonly selectedTemplateDescription = computed<string>(
    () => this.policyService.templates().find((t) => t.key === this.selectedTemplateKey())?.description ?? ""
  );

  // Bound to the conditions editor; the model holds an empty list for a policy without conditions.
  readonly editConditions = computed<ConditionalAccessPolicyCondition[]>(() => this.policyModel().conditions);

  // enforced_since floors the counts only until one full time window has passed since it; after
  // that the backend counts the configured window unchanged, so showing it would be noise. Shown
  // in dry run too, because the trial simulates against the same floor.
  readonly countFloorStillBites = computed(() => {
    const enforcedSince = this.editPolicy().enforced_since;
    if (!enforcedSince) {
      return false;
    }
    // The server sends microsecond precision, which new Date() only parses reliably on some
    // engines - normalize it to the three digits the Date Time String Format allows first.
    const elapsed = (Date.now() - new Date(normalizeDateTimeString(enforcedSince)).getTime()) / 1000;
    return elapsed < this.editPolicy().time_window_seconds;
  });
  // Priorities must be unique across policies, so the evaluation order is unambiguous and the
  // backend 400s otherwise; this surfaces the clashing policy for the inline error, excluding the
  // policy's own id so an unchanged priority is not a self-collision.
  priorityConflict = computed<ConditionalAccessPolicy | undefined>(() => {
    const priority = this.editPolicy().priority;
    if (priority == null) {
      return undefined;
    }
    const currentId = this.editPolicy().id;
    return this.policyService.policies().find((policy) => policy.priority === priority && policy.id !== currentId);
  });
  // The name of the policy while its save request runs. A new policy keeps no id once saved, and the reloaded list
  // already holds it, so the name being saved is not reported as a clash with the policy itself.
  protected readonly savingName = signal<string | null>(null);
  // Names are unique across policies and the backend rejects a second one, so this surfaces the policy that
  // already carries the name. The comparison ignores case and surrounding spaces because the backend strips the
  // name and MySQL and MariaDB ignore case, so the clash is caught where the backend would treat both names as one.
  // The policy's own entry is excluded by id, and a name left unchanged never collides, so an existing case twin
  // stays editable.
  nameConflict = computed<ConditionalAccessPolicy | undefined>(() => {
    const name = this.editPolicy().name;
    if (!name.trim() || name === this.policy().name) {
      return undefined;
    }
    const folded = name.trim().toLowerCase();
    if (folded === this.savingName()?.trim().toLowerCase()) {
      return undefined;
    }
    const currentId = this.editPolicy().id;
    return this.policyService
      .policies()
      .find((policy) => policy.id !== currentId && policy.name.trim().toLowerCase() === folded);
  });
  // The stage rules, as the flags the template needs for the notes under the stages heading. They sit outside any
  // mat-form-field, so they show as soon as a rule fails rather than on touch. The rules of the stage list come from
  // its own errors and the rules of the stages and their actions from the errors beneath each stage.
  private readonly stageListErrorKinds = computed(
    () =>
      new Set(
        this.policyForm
          .stages()
          .errors()
          .map((error) => error.kind)
      )
  );
  private readonly stageRowErrorKinds = computed(() => {
    const kinds = new Set<string>();
    for (const stage of this.policyForm.stages) {
      for (const error of stage().errorSummary()) {
        kinds.add(error.kind);
      }
    }
    return kinds;
  });
  private readonly stageThresholdInvalid = computed(() =>
    [ERR.required, ERR.parse, ERR.min, CA_ERR.notInteger, CA_ERR.stageThreshold].some((kind) =>
      this.stageRowErrorKinds().has(kind)
    )
  );
  stagesValid = computed(() => !this.stageListErrorKinds().has(ERR.required) && !this.stageThresholdInvalid());
  stageThresholdsUnique = computed(() => !this.stageListErrorKinds().has(CA_ERR.stageThresholdDuplicate));
  targetActionsValid = computed(() => !this.stageRowErrorKinds().has(CA_ERR.stageActionNotAllowed));
  stageActionsValid = computed(() => !this.stageRowErrorKinds().has(CA_ERR.stageActionConflict));
  actionValuesValid = computed(() => !this.stageRowErrorKinds().has(CA_ERR.stageActionValue));
  readonly staleConditionValues = computed(() =>
    this.policyService.staleConditionValues(this.policyModel().conditions)
  );

  hasChanges = computed(() => JSON.stringify(this.policy()) !== JSON.stringify(this.editPolicy()));
  canSave = computed(() => this.savingName() === null && this.policyForm().valid());

  // Everything that blocks saving, as the text the admin needs to act on. Save is disabled by a failing check
  // somewhere down the form, sometimes off-screen, so listing the reasons beats leaving the button greyed out with no
  // explanation. The list is read off the errors of the form: each field names its error kinds in the order they are
  // reported, and the fields run in the order of the form.
  saveBlockers = computed<string[]>(() => {
    const blockers = new Set<string>();
    const collectKinds = (kinds: ReadonlySet<string>, messageByKind: Record<string, string>) => {
      // A number input holding text the browser cannot parse reads as empty; the parse error is the reason to show.
      const unparsable = kinds.has(ERR.parse);
      for (const [kind, message] of Object.entries(messageByKind)) {
        if (kinds.has(kind) && !(unparsable && kind === ERR.required)) {
          blockers.add(message);
        }
      }
    };
    const collect = (field: FieldTree<unknown>, messageByKind: Record<string, string>) =>
      collectKinds(
        new Set(
          field()
            .errors()
            .map((error) => error.kind)
        ),
        messageByKind
      );
    const f = this.policyForm;
    collect(f.name, {
      [ERR.required]: $localize`:@@conditionalAccess.nameRequired:Name is required.`,
      [ERR.maxLength]: $localize`:@@conditionalAccess.nameMustNotExceed:Name must not exceed 255 characters.`,
      [ERR.nameTaken]: $localize`:@@conditionalAccess.nameAlreadyUsedBlocker:A policy with this name already exists.`
    });
    const timeWindowMessage = $localize`:@@conditionalAccess.timeWindowMustLeast:Time window must be a whole number of at least 1 second.`;
    collect(f.time_window_value, {
      [ERR.required]: $localize`:@@conditionalAccess.timeWindowRequired:Time window is required.`,
      [CA_ERR.notInteger]: timeWindowMessage,
      [ERR.parse]: timeWindowMessage,
      [ERR.min]: timeWindowMessage
    });
    const priorityMessage = $localize`:@@conditionalAccess.priorityRequiredMustWhole:Priority must be a whole number of at least 1.`;
    collect(f.priority, {
      [ERR.required]: $localize`:@@conditionalAccess.priorityRequired:Priority is required.`,
      [CA_ERR.notInteger]: priorityMessage,
      [ERR.parse]: priorityMessage,
      [ERR.min]: priorityMessage,
      [CA_ERR.priorityTaken]: $localize`:@@conditionalAccess.priorityMustUniqueAcross:Priority must be unique across policies.`
    });
    collect(f.counter_types_to_track, {
      [ERR.required]: $localize`:@@conditionalAccess.selectLeastOneTracked:At least one tracked event type is required.`
    });
    const stageListKinds = this.stageListErrorKinds();
    const stageRowKinds = this.stageRowErrorKinds();
    collectKinds(stageListKinds, {
      [ERR.required]: $localize`:@@conditionalAccess.atLeastOneStageBlocker:At least one stage is required.`
    });
    const thresholdMessage = $localize`:@@conditionalAccess.everyStageNeedsFailure:Every stage needs a failure threshold of at least 1 - or 0 on a stage carrying only DENY.`;
    collectKinds(stageRowKinds, {
      [ERR.required]: $localize`:@@conditionalAccess.failureThresholdRequired:Failure threshold is required.`,
      [ERR.parse]: thresholdMessage,
      [ERR.min]: thresholdMessage,
      [CA_ERR.notInteger]: thresholdMessage,
      [CA_ERR.stageThreshold]: thresholdMessage
    });
    collectKinds(stageListKinds, {
      [CA_ERR.stageThresholdDuplicate]: $localize`:@@conditionalAccess.eachStageMustHave2:Each stage must have a different failure threshold.`
    });
    collectKinds(stageRowKinds, {
      [CA_ERR.stageActionConflict]: $localize`:@@conditionalAccess.stageActionsConflictBlocker:A stage carries the same action twice, or two actions that contradict each other.`,
      [CA_ERR.stageActionNotAllowed]: $localize`:@@conditionalAccess.someActionsNotAllowed2:Some actions are not allowed for the selected target.`,
      [CA_ERR.stageActionValue]: $localize`:@@conditionalAccess.fixHighlightedActionValue:Fix the highlighted action value before saving.`
    });
    collect(f.count_mode, {
      [ERR.required]: $localize`:@@conditionalAccess.countModeRequired:Count Mode is required.`,
      [CA_ERR.countModeNotAllowed]: $localize`:@@conditionalAccess.selectedCountModeNot:The selected count mode is not allowed for the selected target.`
    });
    collect(f.conditions, {
      [CA_ERR.staleConditionValue]: $localize`:@@conditionalAccess.conditionNamesValueNo:A condition names a value that no longer exists: ${this.staleConditionValues()
        .flatMap((stale) => stale.values)
        .join(", ")}.`
    });
    return [...blockers];
  });

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
        this.loadPolicy(EMPTY_CONDITIONAL_ACCESS_POLICY);
        // A brand-new policy starts with empty required fields (name, priority, tracked event types); touching the
        // form shows each "required" hint from the start instead of only after the field has been left.
        void touchAll(this.policyForm);
        this.applyCopyDraft(history.state?.[COPY_DRAFT_STATE_KEY]);
      }
    });

    // Save is blocked for a taken name, so the reason shows at once, also for a name that a template filled in
    // without the field ever being focused.
    effect(() => {
      if (this.nameConflict()) {
        this.policyForm.name().markAsTouched();
      }
    });

    // Changing the target is what makes a count mode unsupported, so the select shows the reason at once instead of
    // waiting for a focus it never received.
    effect(() => {
      if (hasError(this.policyForm.count_mode, CA_ERR.countModeNotAllowed)) {
        this.policyForm.count_mode().markAsTouched();
      }
    });

    // A source-IP policy never resets, and the backend rejects a save that asks it to. The flag is cleared rather than
    // surfaced as an error like the count mode, because there is nothing for the admin to choose; it stays cleared when
    // switching back to a user target, where the control is enabled again and shows what it is set to.
    effect(() => {
      if (this.policyForm.target().value() !== "user" && this.policyForm.reset_on_success().value()) {
        this.updateModel({ reset_on_success: false });
      }
    });

    // Re-initialize once the async list arrives, but only if the user hasn't started editing yet. Only the list
    // triggers it: the edit state is read untracked, because typing a change and then the original value back would
    // otherwise reload the policy, replace the form's rows and rebuild the stage and action items under the cursor.
    effect(() => {
      const policies = this.policyService.policies();
      untracked(() => {
        if (!this.isNewPolicy() && this.editPolicyId && !this.hasChanges()) {
          const found = policies.find((p) => String(p.id) === this.editPolicyId);
          if (found) {
            this.loadPolicy(found);
          }
        }
      });
    });

    this.pendingChangesService.registerHasChanges(() => this.hasChanges());
    this.pendingChangesService.registerSave(this.savePolicy.bind(this));
    this.pendingChangesService.registerValidChanges(() => this.canSave());
  }

  // Seeds both the pristine and the working copy from one policy, each its own deep copy, so editing
  // one cannot reach into the other. The pristine copy is the payload the loaded model maps to, so
  // hasChanges()'s JSON diff compares like with like.
  private loadPolicy(policy: ConditionalAccessPolicySaveParams): void {
    const loaded = toPolicyFormModel(policy);
    this.policy.set(deepCopy(toPolicySaveParams(loaded)));
    this.policyModel.set(loaded);
    this.policyForm().reset();
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  private updateModel(partial: Partial<ConditionalAccessPolicyFormModel>): void {
    this.policyModel.update((model) => ({ ...model, ...partial }));
  }

  onConditionsChange(conditions: ConditionalAccessPolicyCondition[]): void {
    this.updateModel({ conditions });
  }

  // Prefills the whole editor from a shipped template on the create page with a ready-to-POST
  // payload the admin can still edit; a null key clears the prefill back to the empty policy (see
  // clearTemplateSelection).
  applyTemplate(key: string | null): void {
    this.selectedTemplateKey.set(key);
    const template = key ? this.policyService.templates().find((t) => t.key === key) : undefined;
    const prefill = template ? deepCopy(template.policy) : deepCopy(EMPTY_CONDITIONAL_ACCESS_POLICY);
    delete prefill.id;
    // Templates carry no priority: the admin must pick a unique one, so normalize the
    // missing key to null and leave the field empty. A template that states no reset-on-success
    // choice falls back to the backend's default for a user policy, and to cleared for a source-IP
    // one, which never resets, so a prefilled policy cannot start out ticked and disabled.
    // Spelling the types out here makes the compiler enforce both normalizations.
    const policy: ConditionalAccessPolicySaveParams = {
      ...prefill,
      priority: prefill.priority ?? null,
      reset_on_success: prefill.target === "user" ? (prefill.reset_on_success ?? true) : false,
      stages: prefill.stages
    };
    this.policyModel.set(toPolicyFormModel(policy));
  }

  // The copy of a policy arrives from the edit page of that policy as navigation state; it prefills the whole editor
  // like a template, so the name and the priority, which both have to be unique, are validated like any other entry.
  private applyCopyDraft(draft: ConditionalAccessPolicySaveParams | undefined): void {
    if (!draft) {
      return;
    }
    // The draft belongs to the navigation that carried it. Left in the history entry it would come back with
    // the browser's Back button, long after the copy was saved.
    history.replaceState({ ...history.state, [COPY_DRAFT_STATE_KEY]: undefined }, "");
    this.policyModel.set(toPolicyFormModel(draft));
  }

  // Opens the create page with the editor as it is now, unsaved edits included, and leaves the policy being edited as
  // it is stored. The copy carries no id, no priority and no enforcement date: it is a new policy that has to take a
  // priority of its own, and it has not been enforced yet.
  copyPolicy(): void {
    const draft: ConditionalAccessPolicySaveParams = {
      ...deepCopy(this.editPolicy()),
      priority: null,
      enforced_since: null
    };
    delete draft.id;
    this.pendingChangesService.clearAllRegistrations();
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS_NEW, {
      state: { [COPY_DRAFT_STATE_KEY]: draft }
    });
  }

  // The template select's clear button: drops the selected template and resets the prefilled
  // fields back to an empty policy.
  clearTemplateSelection(): void {
    this.applyTemplate(null);
  }

  toggleEnabled(checked: boolean): void {
    this.updateModel({ enabled: checked });
    const id = this.editPolicy().id;
    if (id != null) {
      if (checked) {
        this.policyService.enablePolicy(id);
      } else {
        this.policyService.disablePolicy(id);
      }
    }
  }

  async toggleDryRun(checked: boolean, toggle?: MatSlideToggle): Promise<void> {
    // The question is what to do with the events a trial accumulated, so the *stored* state decides
    // whether there is anything to ask about: a policy being created has no trial, and neither has
    // a stored enforcing policy that was switched to dry run and back without ever being saved.
    if (checked || !this.policy().dry_run) {
      this.updateModel({ dry_run: checked, reset_counters_on_enforce: null });
      return;
    }
    const result = await this.dialogService.openDialogAsync<
      ConditionalAccessDryRunOffDialogData,
      ConditionalAccessDryRunOffDialogResult
    >({
      component: ConditionalAccessDryRunOffDialogComponent,
      data: { policyNames: [this.editPolicy().name] }
    });
    if (!result) {
      // Cancelled: dry_run stays on, but the control already flipped itself to report the click.
      // [checked] is one-way and the value it reads is unchanged, so Angular writes nothing back -
      // put the control where the policy actually is, or the page claims a state it never saved.
      this.resyncDryRunToggle(toggle);
      return;
    }
    this.updateModel({ dry_run: false, reset_counters_on_enforce: result.resetCounters });
  }

  private resyncDryRunToggle(toggle: MatSlideToggle | undefined): void {
    if (toggle) {
      toggle.checked = this.editPolicy().dry_run;
    }
  }

  cancelEdit(): void {
    this.router.navigateByUrl(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS);
  }

  savePolicy(): Promise<boolean> {
    // A second save while one runs would create the policy twice.
    if (this.savingName() !== null) {
      return Promise.resolve(false);
    }
    // The pending-changes dialog enables its save button on the state from when it opened, so a collision that
    // the policy list revealed since then is caught here.
    if (this.nameConflict()) {
      this.notificationService.error(
        $localize`:@@conditionalAccess.nameAlreadyUsedBlocker:A policy with this name already exists.`
      );
      return Promise.resolve(false);
    }
    // The keyboard and pending-changes paths reach here without the disabled Save button in between.
    if (!this.policyForm().valid()) {
      void touchAll(this.policyForm);
      return Promise.resolve(false);
    }
    this.savingName.set(this.editPolicy().name);
    // The engine evaluates stages by descending failure_threshold, so the thresholds the admin
    // entered are the order and nothing extra is derived here.
    const payload: ConditionalAccessPolicySaveParams = { ...this.editPolicy() };
    // An empty list is sent to clear stored conditions, while a policy with none omits the key entirely -
    // otherwise removing the last condition would silently not save.
    if (!payload.conditions?.length && this.policy().conditions?.length) {
      payload.conditions = [];
    }
    return new Promise((resolve) => {
      this.policyService.savePolicy(payload).then((id) => {
        if (id !== undefined) {
          this.pendingChangesService.clearAllRegistrations();
          this.router.navigateByUrl(ROUTE_PATHS.POLICIES_CONDITIONAL_ACCESS);
          resolve(true);
        } else {
          this.savingName.set(null);
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
