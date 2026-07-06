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
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { StickyHeaderDirective } from "@components/shared/directives/sticky-header.directive";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import {
  ALL_AUTH_EVENT_TYPES,
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  EMPTY_LOCKOUT_POLICY,
  LockoutPolicySaveParams,
  LockoutPolicyStage
} from "@services/conditional-access/conditional-access-policy.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { deepCopy } from "@utils/deep-copy.utils";
import { ConditionalAccessStagesListComponent } from "./stages-list/conditional-access-stages-list.component";

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
    ConditionalAccessStagesListComponent
  ],
  templateUrl: "./conditional-access-edit-page.component.html",
  styleUrl: "./conditional-access-edit-page.component.scss"
})
export class ConditionalAccessEditPageComponent implements OnDestroy {
  protected readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly allAuthEventTypes = ALL_AUTH_EVENT_TYPES;
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

  timeWindowValid = computed(() => this.editPolicy().time_window_seconds >= 1);
  priorityValid = computed(() => this.editPolicy().priority >= 1);
  counterTypesValid = computed(() => this.editPolicy().counter_types_to_track.length > 0);
  stagesValid = computed(() => {
    const stages = this.editPolicy().stages;
    return stages.length > 0 && stages.every((stage) => stage.failure_threshold >= 1 && stage.priority >= 1);
  });

  hasChanges = computed(() => JSON.stringify(this.policy()) !== JSON.stringify(this.editPolicy()));
  canSave = computed(
    () =>
      this.policyForm().valid() &&
      this.timeWindowValid() &&
      this.priorityValid() &&
      this.counterTypesValid() &&
      this.stagesValid()
  );

  nameTouched = signal(false);
  showNameError = computed(() => this.nameTouched() && !this.policyForm().valid());

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
        }
      } else {
        this.isNewPolicy.set(true);
        this.editPolicyId = null;
        this.policy.set(deepCopy(EMPTY_LOCKOUT_POLICY));
        this.editPolicy.set(deepCopy(EMPTY_LOCKOUT_POLICY));
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
    this.updateEditPolicy({ counter_types_to_track: counterTypes as LockoutPolicySaveParams["counter_types_to_track"] });
  }

  onTimeWindowInput(value: string): void {
    const parsed = parseInt(value, 10);
    if (!isNaN(parsed) && parsed >= 1) {
      this.updateEditPolicy({ time_window_seconds: parsed });
    }
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
    return new Promise((resolve) => {
      this.policyService.savePolicy(this.editPolicy()).then((id) => {
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
