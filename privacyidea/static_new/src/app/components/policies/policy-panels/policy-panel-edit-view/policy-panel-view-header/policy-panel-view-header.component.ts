import { Component, inject, input, output } from "@angular/core";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatIconModule } from "@angular/material/icon";
import { lastValueFrom } from "rxjs/internal/lastValueFrom";
import { PolicyDetail, PolicyService, PolicyServiceInterface } from "../../../../../services/policies/policies.service";
import {
  SimpleConfirmationDialogData,
  SimpleConfirmationDialogComponent
} from "../../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { DialogServiceInterface, DialogService } from "../../../../../services/dialog/dialog.service";
import { CommonModule } from "@angular/common";
import { MatTooltipModule } from "@angular/material/tooltip";
import { AuthService, AuthServiceInterface } from "../../../../../services/auth/auth.service";
import { CopyPolicyDialogComponent } from "../../../dialog/copy-policy-dialog/copy-policy-dialog.component";

@Component({
  selector: "app-policy-panel-view-header",
  templateUrl: "./policy-panel-view-header.component.html",
  styleUrls: ["./policy-panel-view-header.component.scss"],
  imports: [CommonModule, MatExpansionModule, MatSlideToggleModule, MatIconModule, MatTooltipModule]
})
export class PolicyPanelViewHeaderComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly authService: AuthServiceInterface = inject(AuthService);

  readonly policy = input.required<PolicyDetail>();
  readonly panel = input.required<MatExpansionPanel>();
  readonly isEditMode = input.required<boolean>();
  readonly isEditModeChange = output<boolean>();

  async deletePolicy(policyName: string): Promise<void> {
    if (
      await this._confirm({
        title: "Confirm Deletion",
        confirmAction: {
          type: "destruct",
          label: "Delete",
          value: true
        },
        cancelAction: {
          type: "cancel",
          label: "Cancel",
          value: false
        },
        items: [policyName],
        itemType: "policy"
      })
    ) {
      this.policyService.deletePolicy(policyName);
    }
  }

  togglePolicyActive(policy: PolicyDetail, activate: boolean) {
    if (activate) {
      this.policyService.enablePolicy(policy.name);
    } else {
      this.policyService.disablePolicy(policy.name);
    }
  }
  editPolicy() {
    this.isEditModeChange.emit(true);
    this.panel().open();
  }
  async copyPolicy() {
    const newName = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: CopyPolicyDialogComponent,
          data: this.policy().name
        })
        .afterClosed()
    );
    if (!newName) {
      return;
    }
    this.policyService.copyPolicy(this.policy(), newName);
  }

  async _confirm(data: SimpleConfirmationDialogData): Promise<boolean> {
    return (
      (await lastValueFrom(
        this.dialogService
          .openDialog({
            component: SimpleConfirmationDialogComponent,
            data: data
          })
          .afterClosed()
      )) === true
    );
  }
}
