import { Component, computed, inject, signal } from "@angular/core";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { CommonModule } from "@angular/common";
import { AbstractDialogComponent } from "../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { AbstractControl, ReactiveFormsModule, ValidationErrors, ValidatorFn } from "@angular/forms";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { lastValueFrom } from "rxjs";
import { DialogServiceInterface, DialogService } from "../../../../services/dialog/dialog.service";
import { PolicyServiceInterface, PolicyService, PolicyDetail } from "../../../../services/policies/policies.service";
import {
  SimpleConfirmationDialogData,
  SimpleConfirmationDialogComponent
} from "../../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { DialogAction } from "../../../../models/dialog";
import { PolicyTab } from "../../policies.component";
import { PolicyPanelEditComponent } from "../../policies-table/policy-panels/policy-panel-edit/policy-panel-edit.component";
export function mustBeDifferentValidator(originalValue: string | null): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const isSame = control.value === originalValue;
    return isSame ? { notChanged: true } : null;
  };
}
@Component({
  selector: "app-edit-policy-dialog",
  templateUrl: "./edit-policy-dialog.component.html",
  styleUrls: ["./edit-policy-dialog.component.scss"],
  standalone: true,
  imports: [
    DialogWrapperComponent,
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    PolicyPanelEditComponent
  ]
})
export class EditPolicyDialogComponent extends AbstractDialogComponent<
  { policyDetail: PolicyDetail; mode: "edit" | "create" },
  Partial<PolicyDetail> | null
> {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly policy = signal<PolicyDetail>(this.data.policyDetail);

  readonly policyEdits = signal<Partial<PolicyDetail>>({});
  readonly editedPolicy = computed<PolicyDetail>(() => ({ ...this.policy(), ...this.policyEdits() }));
  readonly isPolicyEdited = computed(() => {
    const currentPolicy = this.policy;
    const editedPolicyFields = this.policyEdits();
    return (
      Object.keys(editedPolicyFields).length > 0 &&
      Object.keys(editedPolicyFields).some((key) => {
        return (currentPolicy as any)[key] !== (editedPolicyFields as any)[key];
      })
    );
  });
  // Component State Signals
  readonly activeTab = signal<PolicyTab>("actions");

  onNameChange(name: string): void {
    this.addPolicyEdit({ name });
  }

  setActiveTab(tab: PolicyTab): void {
    this.activeTab.set(tab);
  }

  togglePolicyActive(policy: PolicyDetail, activate: boolean) {
    if (activate) {
      this.policyService.enablePolicy(policy.name);
    } else {
      this.policyService.disablePolicy(policy.name);
    }
  }

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

    this.policyEdits.set({});
    this.dialogRef.close(null);
  }

  // State-checking Methods
  canSavePolicy(): boolean {
    if (!this.isPolicyEdited()) return false;
    const edits = this.editedPolicy();
    if (edits.name === undefined || edits.name?.trim() === "") {
      return false;
    }
    return true;
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

  selectPolicyScope(scope: string) {
    this.addPolicyEdit({ scope });
  }

  updatePolicyPriority(priority: number) {
    this.addPolicyEdit({ priority });
  }
  updateActions(actions: { [actionName: string]: string }) {
    this.addPolicyEdit({ action: actions });
  }
  addPolicyEdit(edits: Partial<PolicyDetail>) {
    this.policyEdits.set({ ...this.policyEdits(), ...edits });
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

  actions: DialogAction<"submit" | null>[] = [
    {
      label: this.data.mode === "create" ? $localize`Create Policy` : $localize`Save Changes`,
      value: "submit",
      type: "confirm",
      disabled: () => {
        return !this.canSavePolicy();
      }
    }
  ];

  onAction(value: "submit" | null): void {
    if (value === "submit") {
      if (this.data.mode === "create") {
        this.saveNewPolicy();
      } else {
        this.savePolicy();
      }
    }
  }

  savePolicy() {
    if (!this.canSavePolicy()) return;
    this.policyService.savePolicyEdits(this.policy().name, this.policyEdits());
    this.dialogRef.close(this.policyEdits());
  }

  saveNewPolicy() {
    if (!this.canSavePolicy()) return;
    this.policyService.saveNewPolicy({ ...this.policy(), ...this.policyEdits() });
    this.dialogRef.close(this.policyEdits());
  }
}
