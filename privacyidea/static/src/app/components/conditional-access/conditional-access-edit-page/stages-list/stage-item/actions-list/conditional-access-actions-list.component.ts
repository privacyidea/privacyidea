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

import { Component, computed, inject, input } from "@angular/core";
import { FieldTree } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatIconModule } from "@angular/material/icon";
import {
  ConditionalAccessPolicyService,
  ConditionalAccessPolicyServiceInterface,
  ConditionalAccessStageAction,
  ConditionalAccessTarget,
  REDUNDANT_RESTRICTION_PAIRS
} from "@services/conditional-access/conditional-access-policy.service";
import { ConditionalAccessActionItemComponent } from "./action-item/conditional-access-action-item.component";

@Component({
  selector: "app-conditional-access-actions-list",
  standalone: true,
  imports: [MatButtonModule, MatExpansionModule, MatIconModule, ConditionalAccessActionItemComponent],
  templateUrl: "./conditional-access-actions-list.component.html",
  styleUrl: "./conditional-access-actions-list.component.scss"
})
export class ConditionalAccessActionsListComponent {
  private readonly policyService: ConditionalAccessPolicyServiceInterface = inject(ConditionalAccessPolicyService);

  // The action fields of this stage in the policy form; the list adds and removes actions through them and each item
  // edits its own.
  readonly actions = input.required<FieldTree<ConditionalAccessStageAction[]>>();
  readonly target = input<ConditionalAccessTarget>("user");

  protected readonly actionList = computed(() => this.actions()().value());

  // The pairs this stage actually configures, so the warning can name them. The timed half is dead
  // configuration - it changes nothing an admin can observe - and naming both ends is what makes the warning
  // act on: a stage with several actions would otherwise leave the admin to work out which two conflict.
  readonly redundantRestrictionPairs = computed(() => {
    const configured = new Set(this.actionList().map((action) => action.action_type));
    return REDUNDANT_RESTRICTION_PAIRS.filter(
      ([timed, permanent]) => configured.has(timed) && configured.has(permanent)
    );
  });

  onAddAction(): void {
    // Default a new action to one that is valid for the current target and not already taken, so it is
    // never born incompatible (e.g. LOCK_USER under a source_ip policy) and never born in conflict with an
    // action the stage already carries. Both targets allow the repeatable EMAIL_ADMIN, so there is always
    // something left to offer once /targets has answered.
    const unavailable = this.policyService.unavailableActionTypes(this.actionList(), this.target());
    const allowed = this.policyService.actionsForTarget(this.target()).filter((type) => !unavailable.has(type));
    // EMAIL_ADMIN is valid for every target and always repeatable, so it is the one type that is never
    // incompatible even before /targets has answered (when allowed and unavailable are both still empty).
    const actionType = allowed[0] ?? "EMAIL_ADMIN";
    this.actions()().value.update((actions) => [...actions, { action_type: actionType, action_value: null }]);
  }

  onRemoveAction(index: number): void {
    this.actions()().value.update((actions) => actions.filter((_, i) => i !== index));
  }
}
