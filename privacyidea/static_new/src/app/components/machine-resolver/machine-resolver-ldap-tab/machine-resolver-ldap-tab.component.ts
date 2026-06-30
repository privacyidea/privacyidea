/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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

import { Component, input, linkedSignal, OnInit, output, signal } from "@angular/core";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { LdapMachineResolverData, MachineResolverData } from "@services/machine-resolver/machine-resolver.service";

import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { InlineEditFieldComponent } from "@components/machine-resolver/inline-edit-field/inline-edit-field.component";

@Component({
  selector: "app-machine-resolver-ldap-tab",
  templateUrl: "./machine-resolver-ldap-tab.component.html",
  styleUrls: ["./machine-resolver-ldap-tab.component.scss"],
  imports: [
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatButton,
    MatIcon,
    InlineEditFieldComponent
  ],
  standalone: true
})
export class MachineResolverLdapTabComponent implements OnInit {
  readonly isCreateMode = input<boolean>(false);
  readonly canEdit = input<boolean>(false);
  readonly canSave = input<boolean>(false);
  readonly machineResolverData = input.required<MachineResolverData>();
  readonly hostsData = linkedSignal<LdapMachineResolverData>(() => {
    let data = this.machineResolverData() as LdapMachineResolverData;
    data = { ...data, type: "ldap", TIMEOUT: data.TIMEOUT ?? "5" };
    return data;
  });
  readonly newData = output<MachineResolverData>();
  readonly newValidator = output<(data: MachineResolverData) => boolean>();
  readonly saveField = output<void>();
  readonly editingChange = output<boolean>();

  readonly editingKey = signal<string | null>(null);
  private snapshot: MachineResolverData | null = null;

  ngOnInit(): void {
    this.newValidator.emit(this.isValid.bind(this));
  }

  fieldEnabled(key: string): boolean {
    return this.isCreateMode() || this.editingKey() === key;
  }

  startEdit(key: string): void {
    this.snapshot = this.machineResolverData();
    this.editingKey.set(key);
    this.editingChange.emit(true);
  }

  saveEdit(): void {
    this.snapshot = null;
    this.editingKey.set(null);
    this.editingChange.emit(false);
    this.saveField.emit();
  }

  cancelEdit(): void {
    if (this.snapshot) {
      this.newData.emit(this.snapshot);
    }
    this.snapshot = null;
    this.editingKey.set(null);
    this.editingChange.emit(false);
  }

  updateData(
    args:
      | { patch: Partial<LdapMachineResolverData>; remove?: (keyof LdapMachineResolverData)[] }
      | { patch?: Partial<LdapMachineResolverData>; remove: (keyof LdapMachineResolverData)[] }
      | Partial<LdapMachineResolverData>
  ) {
    let patch: Partial<LdapMachineResolverData>;
    let remove: (keyof LdapMachineResolverData)[];
    if ("remove" in args || "patch" in args) {
      const complexArgs = args as {
        patch?: Partial<LdapMachineResolverData>;
        remove?: (keyof LdapMachineResolverData)[];
      };
      patch = complexArgs.patch || {};
      remove = complexArgs.remove || [];
    } else {
      patch = args as Partial<LdapMachineResolverData>;
      remove = [];
    }
    const newData = { ...this.machineResolverData(), ...patch, type: "ldap" };
    if (remove.length > 0) {
      remove.forEach((key) => {
        delete newData[key];
      });
    }
    this.newData.emit(newData);
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

  onClickNoReferrals($event: boolean) {
    this.updateData({ NOREFERRALS: $event ? "True" : "False" });
  }

  preassignActiveDirectoryAttributes() {
    this.updateData({
      SEARCHFILTER: "(objectClass=computer)",
      IDATTRIBUTE: "DN",
      HOSTNAMEATTRIBUTE: "dNSHostName",
      NOREFERRALS: "True"
    });
  }
}
