import { Component, input, linkedSignal, output, ViewEncapsulation } from "@angular/core";
import {
  LdapMachineresolverData,
  MachineresolverData
} from "../../../services/machineresolver/machineresolver.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { FormsModule } from "@angular/forms";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatSelectModule } from "@angular/material/select";

@Component({
  selector: "app-machineresolver-ldap-tab",
  templateUrl: "./machineresolver-ldap-tab.component.html",
  styleUrls: ["./machineresolver-ldap-tab.component.scss"],
  imports: [FormsModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatCheckboxModule],
  standalone: true,
  encapsulation: ViewEncapsulation.ShadowDom
})
export class MachineresolverLdapTabComponent {
  readonly isEditMode = input.required<boolean>();
  readonly machineresolverData = input.required<MachineresolverData>();
  readonly hostsData = linkedSignal<LdapMachineresolverData>(
    () => this.machineresolverData() as LdapMachineresolverData
  );
  readonly onNewData = output<MachineresolverData>();
  readonly onNewValidator = output<(data: MachineresolverData) => boolean>();

  ngOnInit(): void {
    this.onNewValidator.emit(this.isValid.bind(this));
  }

  updateData(
    args:
      | { patch: Partial<LdapMachineresolverData>; remove?: (keyof LdapMachineresolverData)[] }
      | { patch?: Partial<LdapMachineresolverData>; remove: (keyof LdapMachineresolverData)[] }
      | Partial<LdapMachineresolverData>
  ) {
    let patch: Partial<LdapMachineresolverData> = {};
    let remove: (keyof LdapMachineresolverData)[] = [];
    if ("remove" in args || "patch" in args) {
      const complexArgs = args as {
        patch?: Partial<LdapMachineresolverData>;
        remove?: (keyof LdapMachineresolverData)[];
      };
      patch = complexArgs.patch || {};
      remove = complexArgs.remove || [];
    } else {
      patch = args as Partial<LdapMachineresolverData>;
    }
    const newData = { ...this.machineresolverData(), ...patch, type: "ldap" };
    if (remove.length > 0) {
      remove.forEach((key) => {
        delete newData[key];
      });
    }
    this.onNewData.emit(newData);
  }
  updateTlsVerify($event: boolean) {
    this.updateData({ patch: { TLS_VERIFY: $event, TLS_CA_FILE: undefined }, remove: ["TLS_CA_FILE"] });
  }

  isValid(data: MachineresolverData): boolean {
    if (data.type !== "ldap") return false;
    const ldapData = data as LdapMachineresolverData;

    if (!ldapData.LDAPURI || ldapData.LDAPURI.trim() === "") {
      return false;
    }
    if (!ldapData.LDAPBASE || ldapData.LDAPBASE.trim() === "") {
      return false;
    }
    if (!ldapData.BINDDN || ldapData.BINDDN.trim() === "") {
      return false;
    }
    if (!ldapData.BINDPW || ldapData.BINDPW.trim() === "") {
      return false;
    }

    return true;
  }
}
