import { CommonModule } from "@angular/common";
import { Component, effect, inject, input } from "@angular/core";
import { MatIconModule } from "@angular/material/icon";
import { DialogServiceInterface, DialogService } from "../../../../services/dialog/dialog.service";
import { EditPolicyDialogComponent } from "../../dialogs/edit-policy-dialog/edit-policy-dialog.component";
import { AuthServiceInterface, AuthService } from "../../../../services/auth/auth.service";
import { PolicyServiceInterface, PolicyService } from "../../../../services/policies/policies.service";
import { MatButtonModule } from "@angular/material/button";
import {
  SimpleConfirmationDialogComponent,
  SimpleConfirmationDialogData
} from "../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { lastValueFrom } from "rxjs";
import { CopyPolicyDialogComponent } from "@components/policies/dialogs/copy-policy-dialog/copy-policy-dialog.component";

@Component({
  selector: "app-policies-table-actions",
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: "./policies-table-actions.component.html",
  styleUrl: "./policies-table-actions.component.scss"
})
export class PoliciesTableActionsComponent {
  readonly policySelection = input.required<Set<string>>();
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  constructor() {
    effect(() => {
      const selectedPolicies = this.policySelection();
      console.log("Selected policies changed:", selectedPolicies);
      console.log("policySelection().values.length < 1 =", selectedPolicies.size < 1);
    });
  }

  createNewPoilicy() {
    this.dialogService.openDialog({
      component: EditPolicyDialogComponent,
      data: { mode: "create", policyDetail: this.policyService.getEmptyPolicy() }
    });
  }

  async deleteSelectedPolicies() {
    const confirmation = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: SimpleConfirmationDialogComponent,
          data: {
            title: $localize`Delete Policies`,
            items: Array.from(this.policySelection()),
            itemType: $localize`Policies`,
            confirmAction: { label: $localize`Delete`, value: true, type: "destruct" },
            cancelAction: { label: $localize`Cancel`, value: false, type: "cancel" }
          }
        })
        .afterClosed()
    );

    if (!confirmation) {
      return;
    }
    for (const policyName of this.policySelection()) {
      await this.policyService.deletePolicy(policyName);
    }
  }

  async copySelectedPolicies() {
    for (const policyName of this.policySelection()) {
      const newName = await lastValueFrom(
        this.dialogService
          .openDialog({
            component: CopyPolicyDialogComponent,
            data: policyName
          })
          .afterClosed()
      );
      if (newName) {
        try {
          this.policyService.copyPolicy(policyName, newName);
        } catch (e) {
          console.error("Error copying policy:", e);
        }
      }
    }
  }
}
