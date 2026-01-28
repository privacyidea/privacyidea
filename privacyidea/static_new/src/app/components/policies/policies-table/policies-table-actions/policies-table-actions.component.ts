import { CommonModule } from "@angular/common";
import { Component, inject, input } from "@angular/core";
import { MatIconModule } from "@angular/material/icon";
import { DialogServiceInterface, DialogService } from "../../../../services/dialog/dialog.service";
import { EditPolicyDialogComponent } from "../../dialog/edit-policy-dialog/edit-policy-dialog.component";
import { AuthServiceInterface, AuthService } from "../../../../services/auth/auth.service";
import { PolicyServiceInterface, PolicyService } from "../../../../services/policies/policies.service";
import { SimpleConfirmationDialogComponent } from "../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { MatButtonModule } from "@angular/material/button";

@Component({
  selector: "app-policies-table-actions",
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: "./policies-table-actions.component.html",
  styleUrl: "./policies-table-actions.component.scss"
})
export class PoliciesTableActionsComponent {
  copySelectedPolicies() {
    throw new Error("Method not implemented.");
  }
  readonly policySelection = input.required<Set<string>>();
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly policyService: PolicyServiceInterface = inject(PolicyService);

  createNewPoilicy() {
    this.dialogService.openDialog({
      component: EditPolicyDialogComponent,
      data: this.policyService.getEmptyPolicy()
    });
  }

  async deleteSelectedPolicies() {
    const confirmation = await this.dialogService.openDialog({
      component: SimpleConfirmationDialogComponent,
      data: {
        title: "Delete Policies",
        confirmAction: {
          type: "destruct",
          label: "Delete",
          value: true
        },
        items: Array.from(this.policySelection()),
        itemType: "policy"
      }
    });
    if (!confirmation) {
      return;
    }
    for (const policyName of this.policySelection()) {
      await this.policyService.deletePolicy(policyName);
    }
  }
}
