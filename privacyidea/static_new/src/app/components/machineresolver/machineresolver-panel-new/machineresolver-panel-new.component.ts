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
    MachineresolverHostsTabComponent
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
  readonly machineresolverTypes = this.machineresolverService.allMachineresolverTypes;
  readonly machineresolvers = this.machineresolverService.machineresolvers();
  readonly isEdited = computed(() => {
    const current = this.newMachineresolver();
    if (current.resolvername.trim() != "") return true;
    if (Object.keys(current.data).length > 2) return true; // More than resolver and type fields
    return false;
  });
  readonly dataValidatorSignal = signal<(data: MachineresolverData) => boolean>(() => true);

  onDataChange($event: Event) {
    console.log($event);
  }
  // onDataValidatorChange(newValidator: (data: MachineresolverData) => boolean) {
  onDataValidatorChange($event: Event) {
    console.log($event);
    // this.dataValidatorSignal.set(newValidator);
  }

  readonly canSaveMachineresolver = computed(() => {
    const current = this.newMachineresolver();
    if (!current.resolvername) return false;

    const dataValidator = this.dataValidatorSignal();
    return dataValidator(current.data);
  });

  onMachineresolverTypeChange(newType: string) {
    // console.log("Type selection event:", $event);
    // const newType = ($event.target as HTMLSelectElement).value;
    const current = this.newMachineresolver();
    this.newMachineresolver.set({
      ...current,
      type: newType,
      data: { resolver: current.resolvername, type: newType } // Reset data to only have resolver field
    });
  }
  onResolvernameChange(newName: string) {
    // console.log("Name update event:", $event);
    // const newName = ($event.target as HTMLInputElement).value;
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

  saveMachineresolver($panel: MatExpansionPanel) {
    // ...

    this.handleCollapse($panel);
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
          this.newMachineresolver.set(this.machineresolverDetault);
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
