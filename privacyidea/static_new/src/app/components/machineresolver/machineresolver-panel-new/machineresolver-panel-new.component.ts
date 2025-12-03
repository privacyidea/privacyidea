import { Component, computed, inject, signal } from "@angular/core";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatSelectModule } from "@angular/material/select";
import {
  Machineresolver,
  MachineresolverData,
  MachineresolverService,
  MachineresolverServiceInterface
} from "../../../services/machineresolver/machineresolver.service";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import {
  DialogService,
  DialogServiceInterface,
  MatDialogConfigRequired
} from "../../../services/dialog/dialog.service";
import { ConfirmationDialogData } from "../../shared/confirmation-dialog/confirmation-dialog.component";
import { MachineresolverHostsTabComponent } from "../machineresolver-hosts-tab/machineresolver-hosts-tab.component";
import { MachineresolverLdapTabComponent } from "../machineresolver-ldap-tab/machineresolver-ldap-tab.component";

@Component({
  selector: "app-machineresolver-panel-new",
  templateUrl: "./machineresolver-panel-new.component.html",
  styleUrls: ["./machineresolver-panel-new.component.scss"],
  imports: [
    CommonModule,
    MatExpansionModule,
    MatIconModule,
    MatInputModule,
    MatAutocompleteModule,
    MatSelectModule,
    FormsModule,
    MatButtonModule,
    MatInputModule,
    MatAutocompleteModule,
    MatSelectModule,
    MatIcon,
    MachineresolverHostsTabComponent,
    MachineresolverLdapTabComponent
  ]
})
export class MachineresolverPanelNewComponent {
  readonly machineresolverService: MachineresolverServiceInterface = inject(MachineresolverService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly machineresolverDetault: Machineresolver = {
    resolvername: "",
    type: "hosts",
    data: { resolver: "", type: "hosts" }
  };
  readonly newMachineresolver = signal<Machineresolver>(this.machineresolverDetault);
  resetMachineresolver() {
    this.newMachineresolver.set(this.machineresolverDetault);
  }
  readonly machineresolverTypes = this.machineresolverService.allMachineresolverTypes;
  readonly machineresolvers = this.machineresolverService.machineresolvers();
  readonly isEdited = computed(() => {
    const current = this.newMachineresolver();
    if (current.resolvername.trim() != "") return true;
    if (Object.keys(current.data).length > 2) return true; // More than resolver and type fields
    return false;
  });
  readonly dataValidatorSignal = signal<(data: MachineresolverData) => boolean>(() => true);

  onNewData(newData: MachineresolverData) {
    this.newMachineresolver.set({ ...this.newMachineresolver(), data: newData });
  }
  onNewValidator(newValidator: (data: MachineresolverData) => boolean) {
    this.dataValidatorSignal.set(newValidator);
  }

  readonly canSaveMachineresolver = computed(() => {
    const current = this.newMachineresolver();
    if (!current.resolvername.trim()) return false;

    const dataValidator = this.dataValidatorSignal();
    return dataValidator(current.data);
  });

  onMachineresolverTypeChange(newType: string) {
    const current = this.newMachineresolver();
    this.newMachineresolver.set({
      ...current,
      type: newType,
      data: { resolver: current.resolvername, type: newType } // Reset data to only have resolver field
    });
  }
  onResolvernameChange(newName: string) {
    const current = this.newMachineresolver();
    this.newMachineresolver.set({
      ...current,
      resolvername: newName,
      data: { ...current.data, resolver: newName } // Keep data.resolver in sync with name
    });
  }

  onUpdateResolverData(newData: MachineresolverData) {
    if (newData.type !== this.newMachineresolver().type) {
      console.error("Type mismatch between new data and current machineresolver type");
      return;
    }
    const current = this.newMachineresolver();
    this.newMachineresolver.set({
      ...current,
      data: newData
    });
  }

  async saveMachineresolver(panel: MatExpansionPanel) {
    const current = this.newMachineresolver();
    let errorMessage = await this.machineresolverService.postTestMachineresolver(current);
    if (errorMessage) {
      if (errorMessage === "post-failed") {
        const dialogData: MatDialogConfigRequired<ConfirmationDialogData> = {
          data: {
            type: "machineresolver",
            title: "Save machineresolver despite test failure?",
            action: "proceed-despite-error"
          }
        };
        const result = await this.dialogService.confirm(dialogData);
        if (!result) return;
      } else {
        return;
      }
    }
    errorMessage = await this.machineresolverService.postMachineresolver(current);
    if (errorMessage) return;
    this.resetMachineresolver();
    panel.close();
  }

  handleCollapse($panel: MatExpansionPanel) {
    if (!this.isEdited()) {
      this.newMachineresolver.set(this.machineresolverDetault);
      return;
    }
    const dialogData: MatDialogConfigRequired<ConfirmationDialogData> = {
      data: {
        type: "machineresolver",
        title: "Discard changes",
        action: "discard"
      }
    };
    this.dialogService
      .confirm(dialogData)
      .then((result) => {
        if (result) {
          this.resetMachineresolver();
          $panel.close();
        } else {
          $panel.open();
        }
      })
      .catch((err) => {
        console.error("Error handling unsaved changes dialog:", err);
      });
    return;
  }
}
