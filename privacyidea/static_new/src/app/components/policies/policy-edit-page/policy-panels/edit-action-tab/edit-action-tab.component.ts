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

import {
  Component,
  computed,
  inject,
  input,
  linkedSignal,
  output,
  signal,
  Signal,
  WritableSignal
} from "@angular/core";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PolicyActionDetail, PolicyDetail } from "@services/policies/policies.service";
import { ActionSelectorComponent } from "./action-selector/action-selector.component";
import { AddedActionsListComponent } from "./added-actions-list/added-actions-list.component";

@Component({
  selector: "app-edit-action-tab",
  standalone: true,
  imports: [AddedActionsListComponent, ActionSelectorComponent],
  templateUrl: "./edit-action-tab.component.html",
  styleUrl: "./edit-action-tab.component.scss"
})
export class EditActionTabComponent {
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly policy = input.required<PolicyDetail>();
  readonly policyScopeChange = output<string | undefined>();
  readonly actionsUpdate = output<Record<string, string | boolean>>();

  readonly selectedAction: WritableSignal<{ name: string; value: string | boolean } | null> = linkedSignal({
    source: () => ({
      scope: this.policy().scope
    }),
    computation: () => null
  });
  readonly selectedActionDetail = signal<PolicyActionDetail | null>(null);

  readonly actions: Signal<{ name: string; value: string | boolean }[]> = computed(() => {
    const policy = this.policy();
    if (!policy || !policy.action) return [];
    return Object.entries(policy.action).map(([name, value]) => ({ name: name, value }));
  });

  onActionsChange(updatedActions: { name: string; value: string | boolean }[]) {
    const newActions: Record<string, string | boolean> = {};
    updatedActions.forEach((action) => {
      newActions[action.name] = action.value;
    });
    this.actionsUpdate.emit(newActions);
  }

  onActionAdd(event: { action: { name: string; value: string | boolean }; newScope?: string | null }) {
    const { action, newScope } = event;
    const newActions = [...this.actions(), action];
    if (newScope && newScope !== this.policy().scope) {
      this.policyScopeChange.emit(newScope);
    }
    this.onActionsChange(newActions);
    if (this.selectedAction()?.name === action.name) {
      this.selectedAction.set(null);
    }
  }

  onPolicyScopeChange($event: string | undefined) {
    this.policyScopeChange.emit($event);
  }
}
