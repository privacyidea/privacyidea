import { Component, input, linkedSignal, output, ViewEncapsulation } from "@angular/core";
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
  standalone: true,
  encapsulation: ViewEncapsulation.ShadowDom
})
export class MachineresolverHostsTabComponent {
  readonly isEditMode = input.required<boolean>();
  readonly machineresolverData = input.required<MachineresolverData>();
  readonly hostsData = linkedSignal<HostsMachineresolverData>(
    () => this.machineresolverData() as HostsMachineresolverData
  );
  readonly onNewData = output<MachineresolverData>();
  readonly onNewValidator = output<(data: MachineresolverData) => boolean>();

  ngOnInit(): void {
    this.onNewValidator.emit(this.isValid.bind(this));
  }

  updateData(
    args:
      | { patch: Partial<HostsMachineresolverData>; remove?: (keyof HostsMachineresolverData)[] }
      | { patch?: Partial<HostsMachineresolverData>; remove: (keyof HostsMachineresolverData)[] }
      | Partial<HostsMachineresolverData>
  ) {
    let patch: Partial<HostsMachineresolverData> = {};
    let remove: (keyof HostsMachineresolverData)[] = [];
    if ("remove" in args || "patch" in args) {
      const complexArgs = args as {
        patch?: Partial<HostsMachineresolverData>;
        remove?: (keyof HostsMachineresolverData)[];
      };
      patch = complexArgs.patch || {};
      remove = complexArgs.remove || [];
    } else {
      patch = args as Partial<HostsMachineresolverData>;
    }
    const newData = { ...this.machineresolverData(), ...patch, type: "hosts" };
    if (remove.length > 0) {
      remove.forEach((key) => {
        delete newData[key];
      });
    }
    this.onNewData.emit(newData);
  }

  isValid(data: MachineresolverData): boolean {
    if (data.type !== "hosts") return false;
    if ((data as HostsMachineresolverData).filename?.trim() === "") return false;
    return true;
  }
}
