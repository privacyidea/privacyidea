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

import { Component, computed, inject, linkedSignal, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { FormsModule } from "@angular/forms";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule } from "@angular/material/select";
import { MatOptionModule } from "@angular/material/core";
import { MatTooltipModule } from "@angular/material/tooltip";
import { lastValueFrom, map } from "rxjs";

import { DialogServiceInterface, DialogService } from "../../../../../../services/dialog/dialog.service";
import {
  PolicyServiceInterface,
  PolicyService,
  PolicyDetail
} from "../../../../../../services/policies/policies.service";
import { SimpleConfirmationDialogComponent } from "../../../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { PolicyPanelEditComponent } from "../policy-panel-edit/policy-panel-edit.component";

@Component({
  selector: "app-policy-panel-new",
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatSelectModule,
    MatOptionModule,
    MatTooltipModule,
    PolicyPanelEditComponent
  ],
  templateUrl: "./policy-panel-new.component.html",
  styleUrl: "./policy-panel-new.component.scss"
})
export class PolicyPanelNewComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);

  /**
   * Numeric trigger to force state reset.
   */
  private resetTrigger = signal(0);

  /**
   * Reactive Draft State with explicit generic types.
   * <SourceType, DataType>
   */
  readonly newPolicy = linkedSignal<
    {
      base: PolicyDetail;
      scopes: string[];
      trigger: number;
    },
    PolicyDetail
  >({
    source: () => ({
      base: this.policyService.getEmptyPolicy(),
      scopes: this.policyService.allPolicyScopes(),
      trigger: this.resetTrigger()
    }),
    computation: (source) => {
      // Logic for computing the default state
      const defaultScope = source.scopes.length > 0 ? source.scopes[0] : source.base.scope;
      return { ...source.base, scope: defaultScope };
    }
  });

  /**
   * Tracks if the draft has modifications.
   */
  readonly isPolicyEdited = computed(() => {
    return this.policyService.isPolicyEdited(this.newPolicy(), this.policyService.getEmptyPolicy());
  });

  /**
   * Increments the trigger to force linkedSignal re-computation.
   */
  private _triggerInternalReset(): void {
    this.resetTrigger.update((v) => v + 1);
  }

  public onPanelOpened(): void {
    if (!this.isPolicyEdited()) {
      this._triggerInternalReset();
    }
  }

  public async onPanelClosed(panel: MatExpansionPanel): Promise<void> {
    if (this.isPolicyEdited()) {
      const confirmed = await this.resetPolicy();
      if (!confirmed) {
        panel.open();
      }
    }
  }

  public updatePolicy(changes: Partial<PolicyDetail>): void {
    this.newPolicy.set({ ...this.newPolicy(), ...changes });
  }

  public async savePolicy(panel?: MatExpansionPanel): Promise<void> {
    if (!this.canSavePolicy()) return;

    try {
      await this.policyService.saveNewPolicy(this.newPolicy());
      this._triggerInternalReset();
      panel?.close();
    } catch (error) {
      console.error("Policy saving failed:", error);
    }
  }

  public async resetPolicy(panel?: MatExpansionPanel): Promise<boolean> {
    if (!this.isPolicyEdited()) {
      this._triggerInternalReset();
      panel?.close();
      return true;
    }

    const confirmed = await this._confirmDiscard();
    if (confirmed) {
      this._triggerInternalReset();
      panel?.close();
      return true;
    }
    return false;
  }

  private async _confirmDiscard(): Promise<boolean> {
    return lastValueFrom(
      this.dialogService
        .openDialog({
          component: SimpleConfirmationDialogComponent,
          data: {
            title: "Confirm Discard",
            confirmAction: { type: "destruct", label: "Discard", value: true },
            itemType: "New Policy",
            items: []
          }
        })
        .afterClosed()
        .pipe(map((result) => result === true))
    );
  }

  // Domain logic helpers - now correctly typed
  public canSavePolicy(): boolean {
    return this.policyService.canSavePolicy(this.newPolicy());
  }

  public policyHasActions(): boolean {
    return this.policyService.policyHasActions(this.newPolicy());
  }
}
