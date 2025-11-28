import { Component, input, linkedSignal, output } from "@angular/core";
import {
  HostsMachineresolverData,
  LdapMachineresolverData,
  MachineresolverData
} from "../../../services/machineresolver/machineresolver.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { FormsModule } from "@angular/forms";

@Component({
  selector: "app-machineresolver-ldap-tab",
  templateUrl: "./machineresolver-ldap-tab.component.html",
  styleUrls: ["./machineresolver-ldap-tab.component.scss"],
  imports: [MatFormFieldModule, MatInputModule, FormsModule],
  standalone: true
})
export class MachineresolverLdapTabComponent {
  readonly isEditMode = input.required<boolean>();
  readonly machineresolverData = input.required<MachineresolverData>();
  readonly hostsData = linkedSignal<LdapMachineresolverData>(
    () => this.machineresolverData() as LdapMachineresolverData
  );
  readonly dataChange = output<MachineresolverData>();
  readonly dataValidator = output<(data: LdapMachineresolverData) => boolean>();

  constructor() {
    this.dataValidator.emit(this.isValid.bind(this));
  }

  onDataChange(patch: Partial<LdapMachineresolverData>) {
    this.dataChange.emit({ ...this.machineresolverData(), ...patch });
  }

  isValid(data: MachineresolverData): boolean {
    if (data.type !== "ldap") return false;
    const ldapData = data as HostsMachineresolverData;

    console.log("LdapMachineresolverData is valid:", data);
    return true;
  }
}
