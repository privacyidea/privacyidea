import { Component, computed, effect, inject, input, linkedSignal, signal, WritableSignal } from "@angular/core";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import {
  Machineresolver,
  MachineresolverData,
  MachineresolverService,
  MachineresolverServiceInterface
} from "../../../services/machineresolver/machineresolver.service";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import {
  DialogServiceInterface,
  DialogService,
  MatDialogConfigRequired
} from "../../../services/dialog/dialog.service";
import { ConfirmationDialogData } from "../../shared/confirmation-dialog/confirmation-dialog.component";
import { MachineresolverHostsTabComponent } from "../machineresolver-hosts-tab/machineresolver-hosts-tab.component";
import { MachineresolverLdapTabComponent } from "../machineresolver-ldap-tab/machineresolver-ldap-tab.component";

@Component({
  selector: "app-machineresolver-panel-edit",
  templateUrl: "./machineresolver-panel-edit.component.html",
  styleUrls: ["./machineresolver-panel-edit.component.scss"],
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
export class MachineresolverPanelEditComponent {
  deleteMachineresolver(arg0: string) {
    throw new Error("Method not implemented.");
  }
  readonly machineresolverService: MachineresolverServiceInterface = inject(MachineresolverService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly machineresolverTypes = this.machineresolverService.allMachineresolverTypes;
  readonly machineresolvers = this.machineresolverService.machineresolvers();
  readonly isEdited = computed(() => {
    const current = this.currentMachineresolver();
    const original = this.originalMachineresolver();
    return JSON.stringify(current) !== JSON.stringify(original);
  });
  readonly dataValidatorSignal = signal<(data: MachineresolverData) => boolean>(() => true);
  readonly isEditMode = signal<boolean>(false);

  readonly originalMachineresolver = input.required<Machineresolver>();
  readonly editedMachineresolver: WritableSignal<Machineresolver> = linkedSignal({
    source: () => ({ originalMachineresolver: this.originalMachineresolver(), isEditMode: this.isEditMode() }),
    computation: (source) => {
      return deepCopy(source.originalMachineresolver);
    }
  });
  readonly currentMachineresolver = linkedSignal<Machineresolver>(() =>
    this.isEditMode() ? this.editedMachineresolver() : this.originalMachineresolver()
  );
  constructor() {
    effect(() => {
      console.log("Current machineresolver data changed:", this.currentMachineresolver().data);
    });
  }

  onNewData(newData: MachineresolverData) {
    console.log("New data received:", newData);
    this.editedMachineresolver.set({ ...this.currentMachineresolver(), data: newData });
  }
  onNewValidator(newValidator: (data: MachineresolverData) => boolean) {
    this.dataValidatorSignal.set(newValidator);
  }
  readonly canSaveMachineresolver = computed(() => {
    const current = this.currentMachineresolver();
    if (!current.resolvername) return false;

    const dataValidator = this.dataValidatorSignal();
    return dataValidator(current.data);
  });

  onMachineresolverTypeChange(newType: string) {
    // console.log("Type selection event:", $event);
    // const newType = ($event.target as HTMLSelectElement).value;
    console.log("Changing type to:", newType);
    const current = this.currentMachineresolver();
    this.editedMachineresolver.set({
      ...current,
      type: newType,
      data: { resolver: current.resolvername, type: newType } // Reset data to only have resolver field
    });
  }

  onResolvernameChange(newName: string) {
    // console.log("Name update event:", $event);
    // const newName = ($event.target as HTMLInputElement).value;
    const current = this.currentMachineresolver();
    this.editedMachineresolver.set({
      ...current,
      resolvername: newName,
      data: { ...current.data, resolver: newName } // Keep data.resolver in sync with name
    });
  }

  onUpdateResolverData(newData: MachineresolverData) {
    const current = this.currentMachineresolver();
    if (newData.type !== current.type) {
      console.error("Type mismatch between new data and current machineresolver type");
      return;
    }
    this.editedMachineresolver.set({
      ...current,
      data: newData
    });
  }

  saveMachineresolver() {
    // ...
  }

  cancelEditMode() {
    if (!this.isEdited()) {
      this.isEditMode.set(false);
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
          this.isEditMode.set(false);
        }
      })
      .catch((err) => {
        console.error("Error handling unsaved changes dialog:", err);
      });
    return;
  }

  handleCollapse($panel: MatExpansionPanel) {
    if (!this.isEdited()) {
      this.isEditMode.set(false);
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
          this.isEditMode.set(false);
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

// Remove this when the global helper functions is merged
function deepCopy<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}
