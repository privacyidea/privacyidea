/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { Component, computed, input, linkedSignal, output, ViewEncapsulation } from "@angular/core";
import {
  LdapMachineResolverData,
  MachineResolverData
} from "../../../services/machine-resolver/machine-resolver.service";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { FormsModule } from "@angular/forms";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatSelectModule } from "@angular/material/select";

@Component({
  selector: "app-machine-resolver-ldap-tab",
  templateUrl: "./machine-resolver-ldap-tab.component.html",
  styleUrls: ["./machine-resolver-ldap-tab.component.scss"],
  imports: [FormsModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatCheckboxModule],
  standalone: true,
  encapsulation: ViewEncapsulation.ShadowDom
})
export class MachineResolverLdapTabComponent {
  readonly isEditMode = input.required<boolean>();
  readonly machineResolverData = input.required<MachineResolverData>();
  readonly hostsData = linkedSignal<LdapMachineResolverData>(() => {
    let data = this.machineResolverData() as LdapMachineResolverData;
    data = { ...data, type: "ldap", TIMEOUT: data.TIMEOUT ?? "5" };
    return data;
  });
  readonly onNewData = output<MachineResolverData>();
  readonly onNewValidator = output<(data: MachineResolverData) => boolean>();

  readonly isActiveDirectoryAttributesPreassigned = computed<boolean>(() => {
    const data = this.machineResolverData() as LdapMachineResolverData;
    return (
      data.SEARCHFILTER === "(objectClass=computer)" &&
      data.IDATTRIBUTE === "DN" &&
      data.HOSTNAMEATTRIBUTE === "dNSHostName" &&
      data.NOREFERRALS === true
    );
  });

  ngOnInit(): void {
    this.onNewValidator.emit(this.isValid.bind(this));
  }

  updateData(
    args:
      | { patch: Partial<LdapMachineResolverData>; remove?: (keyof LdapMachineResolverData)[] }
      | { patch?: Partial<LdapMachineResolverData>; remove: (keyof LdapMachineResolverData)[] }
      | Partial<LdapMachineResolverData>
  ) {
    let patch: Partial<LdapMachineResolverData> = {};
    let remove: (keyof LdapMachineResolverData)[] = [];
    if ("remove" in args || "patch" in args) {
      const complexArgs = args as {
        patch?: Partial<LdapMachineResolverData>;
        remove?: (keyof LdapMachineResolverData)[];
      };
      patch = complexArgs.patch || {};
      remove = complexArgs.remove || [];
    } else {
      patch = args as Partial<LdapMachineResolverData>;
    }
    const newData = { ...this.machineResolverData(), ...patch, type: "ldap" };
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

  isValid(data: MachineResolverData): boolean {
    if (data.type !== "ldap") return false;
    const ldapData = data as LdapMachineResolverData;

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

  preassignActiveDirectoryAttributes() {
    this.updateData({
      SEARCHFILTER: "(objectClass=computer)",
      IDATTRIBUTE: "DN",
      HOSTNAMEATTRIBUTE: "dNSHostName",
      NOREFERRALS: true
    });
  }
}
