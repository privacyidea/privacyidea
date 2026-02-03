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
import { Component, computed, effect, inject, input } from "@angular/core";
import { AbstractControl, FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatOption } from "@angular/material/core";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatButtonModule } from "@angular/material/button";
import { LDAPResolverData, ResolverService } from "../../../../services/resolver/resolver.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { parseBooleanValue } from "../../../../utils/parse-boolean-value";

@Component({
  selector: "app-ldap-resolver",
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
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
  readonly ldapPresets = [
    {
      name: "OpenLDAP",
      loginName: "uid",
      searchFilter: "(uid=*)(objectClass=inetOrgPerson)",
      userInfo: "{ \"phone\" : \"telephoneNumber\", \"mobile\" : \"mobile\", \"email\" : \"mail\", \"surname\" : \"sn\", \"givenname\" : \"givenName\" }",
      uidType: "entryUUID"
    },
    {
      name: "Active Directory",
      loginName: "sAMAccountName",
      searchFilter: "(sAMAccountName=*)(objectCategory=person)",
      userInfo: "{ \"phone\" : \"telephoneNumber\", \"mobile\" : \"mobile\", \"email\" : \"mail\", \"surname\" : \"sn\", \"givenname\" : \"givenName\" }",
      uidType: "objectGUID"
    }
  ];
  data = input<Partial<LDAPResolverData>>({});
  isEditMode = computed(() => !!this.resolverService.selectedResolverName());
  ldapUriControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  ldapBaseControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  loginNameAttributeControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  ldapSearchFilterControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  userInfoControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  startTlsControl = new FormControl<boolean>(false, { nonNullable: true });

  tlsVersionControl = new FormControl<string>("TLSv1_3", { nonNullable: true });
  tlsVerifyControl = new FormControl<boolean>(true, { nonNullable: true });
  tlsCaFileControl = new FormControl<string>("", { nonNullable: true });
  scopeControl = new FormControl<string>("SUBTREE", { nonNullable: true });
  authTypeControl = new FormControl<string>("simple", { nonNullable: true });
  bindDnControl = new FormControl<string>("", { nonNullable: true });
  bindPwControl = new FormControl<string>("", { nonNullable: true });
  timeoutControl = new FormControl<number>(5, { nonNullable: true });
  cacheTimeoutControl = new FormControl<number>(120, { nonNullable: true });
  sizeLimitControl = new FormControl<number>(500, { nonNullable: true });
  serverPoolRoundsControl = new FormControl<number>(2, { nonNullable: true });
  serverPoolSkipControl = new FormControl<number>(30, { nonNullable: true });
  serverPoolPersistentControl = new FormControl<boolean>(false, { nonNullable: true });
  editableControl = new FormControl<boolean>(false, { nonNullable: true });
  objectClassesControl = new FormControl<string>("", { nonNullable: true });
  dnTemplateControl = new FormControl<string>("", { nonNullable: true });
  multivalueAttributesControl = new FormControl<string>("", { nonNullable: true });
  uidTypeControl = new FormControl<string>("DN", { nonNullable: true });
  recursiveGroupSearchControl = new FormControl<boolean>(false, { nonNullable: true });
  groupSearchFilterControl = new FormControl<string>("", { nonNullable: true });
  groupNameAttributeControl = new FormControl<string>("", { nonNullable: true });
  groupAttributeMappingKeyControl = new FormControl<string>("", { nonNullable: true });
  noReferralsControl = new FormControl<boolean>(false, { nonNullable: true });
  noSchemasControl = new FormControl<boolean>(false, { nonNullable: true });

  controls = computed<Record<string, AbstractControl>>(() => ({
    LDAPURI: this.ldapUriControl,
    STARTTLS: this.startTlsControl,
    LDAPBASE: this.ldapBaseControl,
    LOGINNAMEATTRIBUTE: this.loginNameAttributeControl,
    LDAPSEARCHFILTER: this.ldapSearchFilterControl,
    USERINFO: this.userInfoControl,
    TLS_VERSION: this.tlsVersionControl,
    TLS_VERIFY: this.tlsVerifyControl,
    TLS_CA_FILE: this.tlsCaFileControl,
    SCOPE: this.scopeControl,
    AUTHTYPE: this.authTypeControl,
    BINDDN: this.bindDnControl,
    BINDPW: this.bindPwControl,
    TIMEOUT: this.timeoutControl,
    CACHE_TIMEOUT: this.cacheTimeoutControl,
    SIZELIMIT: this.sizeLimitControl,
    SERVERPOOL_ROUNDS: this.serverPoolRoundsControl,
    SERVERPOOL_SKIP: this.serverPoolSkipControl,
    SERVERPOOL_PERSISTENT: this.serverPoolPersistentControl,
    EDITABLE: this.editableControl,
    OBJECT_CLASSES: this.objectClassesControl,
    DN_TEMPLATE: this.dnTemplateControl,
    MULTIVALUEATTRIBUTES: this.multivalueAttributesControl,
    UIDTYPE: this.uidTypeControl,
    recursive_group_search: this.recursiveGroupSearchControl,
    group_search_filter: this.groupSearchFilterControl,
    group_name_attribute: this.groupNameAttributeControl,
    group_attribute_mapping_key: this.groupAttributeMappingKeyControl,
    NOREFERRALS: this.noReferralsControl,
    NOSCHEMAS: this.noSchemasControl
  }));

  constructor() {
    effect(() => {
      const initial = this.data();
      if (initial.LDAPURI !== undefined) this.ldapUriControl.setValue(initial.LDAPURI, { emitEvent: false });
      if (initial.LDAPBASE !== undefined) this.ldapBaseControl.setValue(initial.LDAPBASE, { emitEvent: false });
      if (initial.LOGINNAMEATTRIBUTE !== undefined) this.loginNameAttributeControl.setValue(initial.LOGINNAMEATTRIBUTE, { emitEvent: false });
      if (initial.LDAPSEARCHFILTER !== undefined) this.ldapSearchFilterControl.setValue(initial.LDAPSEARCHFILTER, { emitEvent: false });
      if (initial.USERINFO !== undefined) this.userInfoControl.setValue(initial.USERINFO, { emitEvent: false });
      if (initial.START_TLS !== undefined) this.startTlsControl.setValue(parseBooleanValue(initial.START_TLS), { emitEvent: false });

      if (initial.TLS_VERSION !== undefined) this.tlsVersionControl.setValue(initial.TLS_VERSION, { emitEvent: false });
      if (initial.TLS_VERIFY !== undefined) this.tlsVerifyControl.setValue(parseBooleanValue(initial.TLS_VERIFY), { emitEvent: false });
      if (initial.TLS_CA_FILE !== undefined) this.tlsCaFileControl.setValue(initial.TLS_CA_FILE, { emitEvent: false });
      if (initial.SCOPE !== undefined) this.scopeControl.setValue(initial.SCOPE, { emitEvent: false });
      if (initial.AUTHTYPE !== undefined) this.authTypeControl.setValue(initial.AUTHTYPE, { emitEvent: false });
      if (initial.BINDDN !== undefined) this.bindDnControl.setValue(initial.BINDDN, { emitEvent: false });
      if (initial.BINDPW !== undefined) this.bindPwControl.setValue(initial.BINDPW, { emitEvent: false });
      if (initial.TIMEOUT !== undefined) this.timeoutControl.setValue(Number(initial.TIMEOUT), { emitEvent: false });
      if (initial.CACHE_TIMEOUT !== undefined) this.cacheTimeoutControl.setValue(Number(initial.CACHE_TIMEOUT), { emitEvent: false });
      if (initial.SIZELIMIT !== undefined) this.sizeLimitControl.setValue(Number(initial.SIZELIMIT), { emitEvent: false });
      if (initial.SERVERPOOL_ROUNDS !== undefined) this.serverPoolRoundsControl.setValue(Number(initial.SERVERPOOL_ROUNDS), { emitEvent: false });
      if (initial.SERVERPOOL_SKIP !== undefined) this.serverPoolSkipControl.setValue(Number(initial.SERVERPOOL_SKIP), { emitEvent: false });
      if (initial.SERVERPOOL_PERSISTENT !== undefined) this.serverPoolPersistentControl.setValue(parseBooleanValue(initial.SERVERPOOL_PERSISTENT), { emitEvent: false });
      if (initial.EDITABLE !== undefined) this.editableControl.setValue(parseBooleanValue(initial.EDITABLE), { emitEvent: false });
      if (initial.OBJECT_CLASSES !== undefined) this.objectClassesControl.setValue(initial.OBJECT_CLASSES, { emitEvent: false });
      if (initial.DN_TEMPLATE !== undefined) this.dnTemplateControl.setValue(initial.DN_TEMPLATE, { emitEvent: false });
      if (initial.MULTIVALUEATTRIBUTES !== undefined) this.multivalueAttributesControl.setValue(initial.MULTIVALUEATTRIBUTES, { emitEvent: false });
      if (initial.UIDTYPE !== undefined) this.uidTypeControl.setValue(initial.UIDTYPE, { emitEvent: false });
      if (initial.recursive_group_search !== undefined) this.recursiveGroupSearchControl.setValue(parseBooleanValue(initial.recursive_group_search), { emitEvent: false });
      if (initial.group_search_filter !== undefined) this.groupSearchFilterControl.setValue(initial.group_search_filter, { emitEvent: false });
      if (initial.group_name_attribute !== undefined) this.groupNameAttributeControl.setValue(initial.group_name_attribute, { emitEvent: false });
      if (initial.group_attribute_mapping_key !== undefined) this.groupAttributeMappingKeyControl.setValue(initial.group_attribute_mapping_key, { emitEvent: false });
      if (initial.NOREFERRALS !== undefined) this.noReferralsControl.setValue(parseBooleanValue(initial.NOREFERRALS), { emitEvent: false });
      if (initial.NOSCHEMAS !== undefined) this.noSchemasControl.setValue(parseBooleanValue(initial.NOSCHEMAS), { emitEvent: false });
    });
  }

  applyLdapPreset(preset: any): void {
    this.loginNameAttributeControl.setValue(preset.loginName);
    this.ldapSearchFilterControl.setValue(preset.searchFilter);
    this.userInfoControl.setValue(preset.userInfo);
    this.uidTypeControl.setValue(preset.uidType);
    this.multivalueAttributesControl.setValue("");
  }
}
