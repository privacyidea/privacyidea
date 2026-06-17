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

import { Component, computed, effect, inject, input, signal } from "@angular/core";
import { form, FormField, required } from "@angular/forms/signals";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatOption, MatSelect, MatSelectModule } from "@angular/material/select";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { BindType, LdapPreset, LDAPResolverData, ResolverService } from "@services/resolver/resolver.service";
import { parseBooleanValue } from "@utils/parse-boolean-value";

interface LdapFormModel {
  SCOPE: string;
  LDAPBASE: string;
  LDAPURI: string;
  START_TLS: boolean;
  TLS_VERSION: string;
  TLS_VERIFY: boolean;
  TLS_CA_FILE: string;
  AUTHTYPE: BindType;
  BINDPW: string;
  BINDDN: string;
  TIMEOUT: number;
  CACHE_TIMEOUT: number;
  SIZELIMIT: number;
  SERVERPOOL_ROUNDS: number;
  SERVERPOOL_SKIP: number;
  SERVERPOOL_PERSISTENT: boolean;
  EDITABLE: boolean;
  OBJECT_CLASSES: string;
  DN_TEMPLATE: string;
  LOGINNAMEATTRIBUTE: string;
  UIDTYPE: string;
  LDAPSEARCHFILTER: string;
  USERINFO: string;
  MULTIVALUEATTRIBUTES: string;
  recursive_group_search: boolean;
  group_base_dn: string;
  group_search_filter: string;
  group_name_attribute: string;
  group_attribute_mapping_key: string;
  NOREFERRALS: boolean;
  NOSCHEMAS: boolean;
}

@Component({
  selector: "app-ldap-resolver",
  standalone: true,
  imports: [
    FormField,
    MatFormField,
    MatLabel,
    MatInput,
    MatError,
    MatSelectModule,
    MatSelect,
    MatOption,
    MatCheckboxModule,
    MatButtonModule,
    ClearableInputComponent
  ],
  templateUrl: "./ldap-resolver.component.html",
  styleUrl: "./ldap-resolver.component.scss"
})
export class LdapResolverComponent {
  private readonly resolverService = inject(ResolverService);
  readonly ldapPresets: LdapPreset[] = [
    {
      name: "OpenLDAP",
      loginName: "uid",
      searchFilter: "(uid=*)(objectClass=inetOrgPerson)",
      userInfo:
        '{ "phone" : "telephoneNumber", "mobile" : "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }',
      uidType: "entryUUID"
    },
    {
      name: "Active Directory",
      loginName: "sAMAccountName",
      searchFilter: "(sAMAccountName=*)(objectCategory=person)",
      userInfo:
        '{ "phone" : "telephoneNumber", "mobile" : "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }',
      uidType: "objectGUID"
    }
  ];
  data = input<Partial<LDAPResolverData>>({});
  isEditMode = computed(() => !!this.resolverService.selectedResolverName());

  model = signal<LdapFormModel>({
    SCOPE: "SUBTREE",
    LDAPBASE: "",
    LDAPURI: "",
    START_TLS: true,
    TLS_VERSION: "TLSv1_3",
    TLS_VERIFY: true,
    TLS_CA_FILE: "",
    AUTHTYPE: "Simple",
    BINDPW: "",
    BINDDN: "",
    TIMEOUT: 5,
    CACHE_TIMEOUT: 120,
    SIZELIMIT: 500,
    SERVERPOOL_ROUNDS: 2,
    SERVERPOOL_SKIP: 30,
    SERVERPOOL_PERSISTENT: false,
    EDITABLE: false,
    OBJECT_CLASSES: "",
    DN_TEMPLATE: "",
    LOGINNAMEATTRIBUTE: "",
    UIDTYPE: "DN",
    LDAPSEARCHFILTER: "",
    USERINFO: "",
    MULTIVALUEATTRIBUTES: "",
    recursive_group_search: false,
    group_base_dn: "",
    group_search_filter: "",
    group_name_attribute: "",
    group_attribute_mapping_key: "",
    NOREFERRALS: false,
    NOSCHEMAS: false
  });

  ldapForm = form(this.model, (f) => {
    required(f.LDAPBASE);
    required(f.LDAPURI);
    required(f.LOGINNAMEATTRIBUTE);
    required(f.LDAPSEARCHFILTER);
    required(f.USERINFO);
  });

  isValid = () => this.ldapForm().valid();
  isDirty = () => this.ldapForm().dirty();
  getValue = () => this.model();

  // Computed TLS state
  isLdapsUri = computed(() => (this.model().LDAPURI || "").startsWith("ldaps:"));
  isLdapUri = computed(() => (this.model().LDAPURI || "").startsWith("ldap:"));

  get showTls(): boolean {
    return this.isLdapUri() || this.isLdapsUri();
  }

  startTlsDisabled = computed(() => this.isLdapsUri());
  tlsVersionDisabled = computed(() => !this.model().START_TLS || this.isLdapsUri());
  tlsVerifyDisabled = computed(() => !this.model().START_TLS || this.isLdapsUri());
  tlsCaFileDisabled = computed(() => !this.model().START_TLS || !this.model().TLS_VERIFY || this.isLdapsUri());
  tlsCaFileRequired = computed(() => this.model().START_TLS && this.model().TLS_VERIFY && !this.isLdapsUri());

  constructor() {
    effect(() => {
      const initial = this.data();
      this.model.update((m) => ({
        ...m,
        ...(initial.SCOPE !== undefined ? { SCOPE: initial.SCOPE } : {}),
        ...(initial.LDAPBASE !== undefined ? { LDAPBASE: initial.LDAPBASE } : {}),
        ...(initial.LDAPURI !== undefined ? { LDAPURI: initial.LDAPURI } : {}),
        ...(initial.START_TLS !== undefined ? { START_TLS: parseBooleanValue(initial.START_TLS) } : {}),
        ...(initial.TLS_VERSION !== undefined ? { TLS_VERSION: initial.TLS_VERSION } : {}),
        ...(initial.TLS_VERIFY !== undefined ? { TLS_VERIFY: parseBooleanValue(initial.TLS_VERIFY) } : {}),
        ...(initial.TLS_CA_FILE !== undefined ? { TLS_CA_FILE: initial.TLS_CA_FILE } : {}),
        ...(initial.AUTHTYPE !== undefined ? { AUTHTYPE: initial.AUTHTYPE } : {}),
        ...(initial.BINDPW !== undefined ? { BINDPW: initial.BINDPW } : {}),
        ...(initial.BINDDN !== undefined ? { BINDDN: initial.BINDDN } : {}),
        ...(initial.TIMEOUT !== undefined ? { TIMEOUT: Number(initial.TIMEOUT) } : {}),
        ...(initial.CACHE_TIMEOUT !== undefined ? { CACHE_TIMEOUT: Number(initial.CACHE_TIMEOUT) } : {}),
        ...(initial.SIZELIMIT !== undefined ? { SIZELIMIT: Number(initial.SIZELIMIT) } : {}),
        ...(initial.SERVERPOOL_ROUNDS !== undefined ? { SERVERPOOL_ROUNDS: Number(initial.SERVERPOOL_ROUNDS) } : {}),
        ...(initial.SERVERPOOL_SKIP !== undefined ? { SERVERPOOL_SKIP: Number(initial.SERVERPOOL_SKIP) } : {}),
        ...(initial.SERVERPOOL_PERSISTENT !== undefined
          ? { SERVERPOOL_PERSISTENT: parseBooleanValue(initial.SERVERPOOL_PERSISTENT) }
          : {}),
        ...(initial.EDITABLE !== undefined ? { EDITABLE: parseBooleanValue(initial.EDITABLE) } : {}),
        ...(initial.OBJECT_CLASSES !== undefined ? { OBJECT_CLASSES: initial.OBJECT_CLASSES } : {}),
        ...(initial.DN_TEMPLATE !== undefined ? { DN_TEMPLATE: initial.DN_TEMPLATE } : {}),
        ...(initial.LOGINNAMEATTRIBUTE !== undefined ? { LOGINNAMEATTRIBUTE: initial.LOGINNAMEATTRIBUTE } : {}),
        ...(initial.UIDTYPE !== undefined ? { UIDTYPE: initial.UIDTYPE } : {}),
        ...(initial.LDAPSEARCHFILTER !== undefined ? { LDAPSEARCHFILTER: initial.LDAPSEARCHFILTER } : {}),
        ...(initial.USERINFO !== undefined ? { USERINFO: initial.USERINFO } : {}),
        ...(initial.MULTIVALUEATTRIBUTES !== undefined ? { MULTIVALUEATTRIBUTES: initial.MULTIVALUEATTRIBUTES } : {}),
        ...(initial.recursive_group_search !== undefined
          ? { recursive_group_search: parseBooleanValue(initial.recursive_group_search) }
          : {}),
        ...(initial.group_base_dn !== undefined ? { group_base_dn: initial.group_base_dn } : {}),
        ...(initial.group_search_filter !== undefined ? { group_search_filter: initial.group_search_filter } : {}),
        ...(initial.group_name_attribute !== undefined ? { group_name_attribute: initial.group_name_attribute } : {}),
        ...(initial.group_attribute_mapping_key !== undefined
          ? { group_attribute_mapping_key: initial.group_attribute_mapping_key }
          : {}),
        ...(initial.NOREFERRALS !== undefined ? { NOREFERRALS: parseBooleanValue(initial.NOREFERRALS) } : {}),
        ...(initial.NOSCHEMAS !== undefined ? { NOSCHEMAS: parseBooleanValue(initial.NOSCHEMAS) } : {})
      }));
      this.ldapForm().reset();
    });
  }

  applyLdapPreset(preset: LdapPreset): void {
    this.model.update((m) => ({
      ...m,
      LOGINNAMEATTRIBUTE: preset.loginName,
      LDAPSEARCHFILTER: preset.searchFilter,
      USERINFO: preset.userInfo,
      UIDTYPE: preset.uidType,
      MULTIVALUEATTRIBUTES: ""
    }));
  }
}
