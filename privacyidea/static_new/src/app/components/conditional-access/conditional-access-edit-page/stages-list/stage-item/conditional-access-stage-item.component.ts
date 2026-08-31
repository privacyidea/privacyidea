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

import { Component, computed, input, output, signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import {
  ConditionalAccessPolicyStage,
  ConditionalAccessStageAction,
  ConditionalAccessTarget
} from "@services/conditional-access/conditional-access-policy.service";
import { ErrorStateDirective } from "@components/shared/directives/error-state.directive";
import { ConditionalAccessActionsListComponent } from "./actions-list/conditional-access-actions-list.component";

// The actions that state a standing verdict instead of reacting to a failure count. Only a stage
// carrying nothing but these may use threshold 0, mirroring _validate_threshold_for_actions in
// lib/conditional_access/policy.py.
const STANDING_DECISION_ACTIONS: string[] = ["DENY"];

@Component({
  selector: "app-conditional-access-stage-item",
  standalone: true,
  imports: [
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    ErrorStateDirective,
    ConditionalAccessActionsListComponent
  ],
  templateUrl: "./conditional-access-stage-item.component.html",
  styleUrl: "./conditional-access-stage-item.component.scss"
})
export class ConditionalAccessStageItemComponent {
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

  onActionsChange(actions: ConditionalAccessStageAction[]): void {
    this.updateStage.emit({ actions });
  }

  onRemoveStage(): void {
    this.removeStage.emit();
  }
}
