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

import { Component, computed, inject, input, linkedSignal, model, output, viewChild } from "@angular/core";
import { MatTabsModule } from "@angular/material/tabs";

import { EditActionTabComponent } from "@components/policies/policy-edit-page/policy-panels/edit-action-tab/edit-action-tab.component";
import { EditConditionsTabComponent } from "@components/policies/policy-edit-page/policy-panels/edit-conditions-tab/edit-conditions-tab.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PolicyDetail } from "@services/policies/policies.service";
import { PolicyDescriptionEditComponent } from "./policy-description/policy-description-edit.component";
import { PolicyNameEditComponent } from "./policy-name-edit/policy-name-edit.component";
import { PolicyPriorityEditComponent } from "./policy-priority-edit/policy-priority-edit.component";
import { PolicyScopeEditComponent } from "./policy-scope-edit/policy-scope-edit.component";

export type PolicyTab = "actions" | "conditions";

@Component({
  selector: "app-policy-panel-edit",
  standalone: true,
  imports: [
    MatTabsModule,
    EditActionTabComponent,
    EditConditionsTabComponent,
    PolicyDescriptionEditComponent,
    PolicyPriorityEditComponent,
    PolicyNameEditComponent,
    PolicyScopeEditComponent
  ],
  templateUrl: "./policy-panel-edit.component.html",
  styleUrl: "./policy-panel-edit.component.scss"
})
export class PolicyPanelEditComponent {
  private readonly dialogService: DialogServiceInterface = inject(DialogService);

  /**
   * Initial policy data from parent.
   */
  readonly policy = input.required<PolicyDetail>();

  /**
   * Notifies the parent about any attribute changes.
   */
  readonly policyEdit = output<Partial<PolicyDetail>>();

  readonly activeTab = model<PolicyTab>("actions");
  readonly actionFilter = model<string>("");

  /** Set while another policy already carries the edited name. */
  readonly nameTaken = input<boolean>(false);

  /** Set while the page header has taken the search field over, so the tab hides its own. */
  readonly searchInHeader = input<boolean>(false);

  private readonly actionTab = viewChild(EditActionTabComponent);
  private readonly nameEdit = viewChild(PolicyNameEditComponent);
  private readonly priorityEdit = viewChild(PolicyPriorityEditComponent);
  readonly searchAnchor = computed(() => this.actionTab()?.searchAnchor().nativeElement);
  readonly searchField = computed(() => this.actionTab()?.searchField());

  readonly tabValues: PolicyTab[] = ["actions", "conditions"];
  readonly tabIndex = computed(() => this.tabValues.indexOf(this.activeTab()));

  /**
   * Puffer for local changes.
   * It resets to an empty object whenever the source 'policy' input changes.
   */
  readonly policyEdits = linkedSignal<PolicyDetail, Partial<PolicyDetail>>({
    source: () => this.policy(),
    computation: () => ({}) // Reset local edits if a new policy is loaded
  });

  /**
   * Merged view of the original policy and local edits.
   */
  readonly editedPolicy = computed<PolicyDetail>(() => ({
    ...this.policy(),
    ...this.policyEdits()
  }));

  /**
   * Helper to check if the current draft has unsaved changes.
   */
  readonly isPolicyEdited = computed(() => Object.keys(this.policyEdits()).length > 0);
  /**
   * True while the name and the priority satisfy their rules, a scope is chosen and every added action holds a
   * value that suits it. The backend rejects a priority below 1, and a policy without a scope cannot be saved.
   */
  readonly valid = computed(
    () =>
      !!this.nameEdit()?.valid() &&
      !!this.priorityEdit()?.valid() &&
      !!this.editedPolicy().scope &&
      (this.actionTab()?.valid() ?? true)
  );
  readonly policyHasActions = computed(() => Object.keys(this.editedPolicy().action ?? {}).length > 0);

  public setActiveTab(tab: PolicyTab): void {
    this.activeTab.set(tab);
  }

  public onTabIndexChange(index: number): void {
    const tab = this.tabValues[index];
    if (tab) {
      this.setActiveTab(tab);
    }
  }

  /**
   * Stores a local edit and propagates it to the parent.
   */
  public addPolicyEdit(edits: Partial<PolicyDetail>): void {
    this.policyEdits.set({ ...this.policyEdits(), ...edits });
    this.policyEdit.emit(edits);
  }

  /**
   * Stores the priority. An empty field is not a priority: the policy keeps its last number and the priority field
   * reports the missing value through {@link valid}.
   */
  public onPriorityChange(priority: number | null): void {
    if (priority !== null) {
      this.addPolicyEdit({ priority });
    }
  }

  public updateActions(actions: Record<string, string | boolean>): void {
    this.addPolicyEdit({ action: actions });
  }

  /**
   * Handles scope changes with a safety confirmation if actions are present.
   */
  public async onPolicyScopeChange(newScope?: string): Promise<void> {
    const currentActions = this.editedPolicy().action;

    if (currentActions && Object.keys(currentActions).length > 0) {
      const confirm = await this.dialogService.confirm({
        title: $localize`:@@policy.changePolicyScope:Change Policy Scope`,
        message: $localize`:@@policy.changingPolicy:Changing the policy scope will remove all currently added actions. Do you want to proceed?`,
        confirmButtonText: $localize`:@@policy.yesChangeScope:Yes, change scope`
      });

      if (!confirm) return;

      // Clear actions on scope change
      this.addPolicyEdit({ scope: newScope, action: {} });
    } else {
      this.addPolicyEdit({ scope: newScope });
    }
  }
}
