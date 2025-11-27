import { Component, input, linkedSignal, output } from "@angular/core";
import {
  HostsMachineresolverData,
  MachineresolverData
} from "../../../services/machineresolver/machineresolver.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { FormsModule } from "@angular/forms";

@Component({
  selector: "app-machineresolver-hosts-tab",
  templateUrl: "./machineresolver-hosts-tab.component.html",
  styleUrls: ["./machineresolver-hosts-tab.component.scss"],
  imports: [MatFormFieldModule, MatInputModule, FormsModule],
  standalone: true
})
export class MachineresolverHostsTabComponent {
  readonly isEditMode = input.required<boolean>();
  readonly machineresolverData = input.required<MachineresolverData>();
  readonly hostsData = linkedSignal<HostsMachineresolverData>(
    () => this.machineresolverData() as HostsMachineresolverData
  );
  readonly dataChange = output<MachineresolverData>();
  readonly dataValidator = output<(data: HostsMachineresolverData) => boolean>();

  constructor() {
    this.dataValidator.emit(this.isValid.bind(this));
  }

  onDataChange(patch: Partial<HostsMachineresolverData>) {
    this.dataChange.emit({ ...this.machineresolverData(), ...patch });
  }

  isValid(data: MachineresolverData): boolean {
    if (data.type !== "hosts") return false;
    if ((data as HostsMachineresolverData).filename?.trim() === "") return false;
    console.log("HostsMachineresolverData is valid:", data);
    return true;
  }
}
