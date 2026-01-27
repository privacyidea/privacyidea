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
import { MatInputModule } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { CommonModule } from "@angular/common";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { FormsModule } from "@angular/forms";

@Component({
  selector: "app-policy-panel-edit-header",
  templateUrl: "./policy-panel-edit-header.component.html",
  styleUrls: ["./policy-panel-edit-header.component.scss"],
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatSlideToggleModule,
    MatIconModule,
    MatInputModule,
    MatSelect,
    MatAutocompleteModule
  ]
})
export class PolicyPanelEditHeaderComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly policy = input.required<PolicyDetail>();
  readonly currentPolicy = input.required<PolicyDetail>();
  readonly panel = input.required<MatExpansionPanel>();
  readonly isEditMode = input.required<boolean>();
  readonly isEditModeChange = output<boolean>();
  readonly isPolicyEdited = input.required<boolean>();
  readonly policyEdits = input.required<Partial<PolicyDetail>>();
  readonly policyEditsChange = output<Partial<PolicyDetail>>();

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
  async cancelEditMode() {
    if (!(await this.confirmDiscardChanges())) return;
    this.policyEditsChange.emit({});
    this.isEditModeChange.emit(false);
  }
  async confirmDiscardChanges(): Promise<boolean> {
    if (this.isPolicyEdited()) {
      return this._confirm({
        title: "Discard Changes",
        confirmAction: {
          type: "destruct",
          label: "Discard",
          value: true
        },
        cancelAction: {
          type: "cancel",
          label: "Keep Editing",
          value: false
        },
        items: [],
        itemType: ""
      });
    }
    return true;
  }

  onNameChange(name: string) {
    this.addPolicyEdit({ name });
  }

  selectPolicyScope(scope: string) {
    this.addPolicyEdit({ scope });
  }

  addPolicyEdit(edits: Partial<PolicyDetail>) {
    this.policyEditsChange.emit({ ...this.policyEdits(), ...edits });
  }

  togglePolicyActive(policy: PolicyDetail, activate: boolean) {
    if (activate) {
      this.policyService.enablePolicy(policy.name);
    } else {
      this.policyService.disablePolicy(policy.name);
    }
  }
  savePolicy() {
    if (!this.canSavePolicy()) return;

    this.policyService.savePolicyEdits(this.policy().name, this.policyEdits());

    this.isEditModeChange.emit(false);
    this.policyEditsChange.emit({});
  }
  canSavePolicy(): boolean {
    if (!this.isPolicyEdited()) return false;
    const edits = this.policyEdits();
    if (edits.name !== undefined && edits.name?.trim() === "") {
      return false;
    }
    return true;
  }

  onPriorityChange($event: string) {
    const priority = parseInt($event, 10);
    if (!isNaN(priority)) {
      this.addPolicyEdit({ priority });
    }
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
