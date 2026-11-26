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

import { Component, effect, input, linkedSignal, output, untracked } from "@angular/core";
import { disabled, form, FormField } from "@angular/forms/signals";
import { MatButton } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { LdapMachineResolverData, MachineResolverData } from "@services/machine-resolver/machine-resolver.service";
import { ERR, requiredNonBlank } from "@utils/form-rules.utils";
import { hasError, touchAll } from "@utils/form-state.utils";

interface LdapFormModel {
  LDAPURI: string;
  TLS_VERIFY: boolean;
  TLS_CA_FILE: string;
  LDAPBASE: string;
  BINDDN: string;
  BINDPW: string;
  AUTHTYPE: string;
  TIMEOUT: string;
  SIZELIMIT: string;
  NOREFERRALS: boolean;
  IDATTRIBUTE: string;
  SEARCHFILTER: string;
  HOSTNAMEATTRIBUTE: string;
  IPATTRIBUTE: string;
}

type LdapTextKey = {
  [K in keyof LdapFormModel]: LdapFormModel[K] extends string ? K : never;
}[keyof LdapFormModel];

// The timeout input shows 5 while the data holds no timeout.
const DEFAULT_TIMEOUT = "5";

const TEXT_KEYS: readonly LdapTextKey[] = [
  "LDAPURI",
  "TLS_CA_FILE",
  "LDAPBASE",
  "BINDDN",
  "BINDPW",
  "AUTHTYPE",
  "TIMEOUT",
  "SIZELIMIT",
  "IDATTRIBUTE",
  "SEARCHFILTER",
  "HOSTNAMEATTRIBUTE",
  "IPATTRIBUTE"
];

function defaultText(key: LdapTextKey): string {
  return key === "TIMEOUT" ? DEFAULT_TIMEOUT : "";
}

function toFormModel(source: MachineResolverData): LdapFormModel {
  const data = source as LdapMachineResolverData;
  return {
    LDAPURI: data.LDAPURI ?? "",
    TLS_VERIFY: !!data.TLS_VERIFY,
    TLS_CA_FILE: data.TLS_CA_FILE ?? "",
    LDAPBASE: data.LDAPBASE ?? "",
    BINDDN: data.BINDDN ?? "",
    BINDPW: data.BINDPW ?? "",
    AUTHTYPE: data.AUTHTYPE ?? "",
    TIMEOUT: data.TIMEOUT ?? DEFAULT_TIMEOUT,
    SIZELIMIT: data.SIZELIMIT ?? "",
    NOREFERRALS: data.NOREFERRALS === "True",
    IDATTRIBUTE: data.IDATTRIBUTE ?? "",
    SEARCHFILTER: data.SEARCHFILTER ?? "",
    HOSTNAMEATTRIBUTE: data.HOSTNAMEATTRIBUTE ?? "",
    IPATTRIBUTE: data.IPATTRIBUTE ?? ""
  };
}

// A key the base data did not hold and the form still shows at its initial value stays absent from the emitted data.
// The CA file only applies while TLS Verify is on, so it is dropped otherwise.
function toData(model: LdapFormModel, base: MachineResolverData): LdapMachineResolverData {
  const data = { ...(base as LdapMachineResolverData), type: "ldap" } as LdapMachineResolverData;
  const record = data as unknown as Record<string, unknown>;
  for (const key of TEXT_KEYS) {
    if (data[key] === undefined && model[key] === defaultText(key)) {
      continue;
    }
    record[key] = model[key];
  }
  if (data.TLS_VERIFY !== undefined || model.TLS_VERIFY) {
    data.TLS_VERIFY = model.TLS_VERIFY;
  }
  if (data.NOREFERRALS !== undefined || model.NOREFERRALS) {
    data.NOREFERRALS = model.NOREFERRALS ? "True" : "False";
  }
  if (!model.TLS_VERIFY) {
    delete data.TLS_CA_FILE;
  }
  return data;
}

@Component({
  selector: "app-machine-resolver-ldap-tab",
  templateUrl: "./machine-resolver-ldap-tab.component.html",
  styleUrls: ["./machine-resolver-ldap-tab.component.scss"],
  imports: [FormField, MatFormFieldModule, MatInputModule, MatSelectModule, MatCheckboxModule, MatButton, MatIcon],
  standalone: true
})
export class MachineResolverLdapTabComponent {
  protected readonly ERR = ERR;
  protected readonly hasError = hasError;

  readonly canEdit = input<boolean>(false);
  // The default data is read while the details page evaluates the validity of a tab whose inputs are not bound yet.
  readonly machineResolverData = input<MachineResolverData>({ resolver: "", type: "ldap" });
  readonly newData = output<MachineResolverData>();

  readonly model = linkedSignal<LdapFormModel>(() => toFormModel(this.machineResolverData()));
  readonly ldapForm = form(this.model, (f) => {
    requiredNonBlank(f.LDAPURI);
    requiredNonBlank(f.LDAPBASE);
    requiredNonBlank(f.BINDDN);
    requiredNonBlank(f.BINDPW);
    disabled(f, () => !this.canEdit());
    disabled(f.TLS_CA_FILE, () => !this.model().TLS_VERIFY);
  });

  readonly isValid = () => this.ldapForm().valid();
  readonly touchAll = () => touchAll(this.ldapForm);

  constructor() {
    effect(() => {
      const model = this.model();
      const base = untracked(() => this.machineResolverData());
      if (JSON.stringify(model) !== JSON.stringify(toFormModel(base))) {
        this.newData.emit(toData(model, base));
      }
    });
  }

  preassignActiveDirectoryAttributes() {
    this.model.update((model) => ({
      ...model,
      SEARCHFILTER: "(objectClass=computer)",
      IDATTRIBUTE: "DN",
      HOSTNAMEATTRIBUTE: "dNSHostName",
      NOREFERRALS: true
    }));
  }
}
