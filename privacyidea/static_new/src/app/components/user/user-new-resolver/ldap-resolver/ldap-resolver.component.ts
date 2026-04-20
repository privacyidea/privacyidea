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

import { Component, inject, input, computed, effect } from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { FormsModule, ReactiveFormsModule, FormControl, Validators, AbstractControl } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatInput } from "@angular/material/input";
import { MatFormField, MatLabel, MatError } from "@angular/material/form-field";
import { MatSelectModule, MatSelect, MatOption } from "@angular/material/select";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { merge } from "rxjs";
import { ResolverService, LdapPreset, LDAPResolverData, BindType } from "src/app/services/resolver/resolver.service";
import { parseBooleanValue } from "src/app/utils/parse-boolean-value";

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

  // --- Connection Details ---
  scopeControl = new FormControl<string>("SUBTREE", { nonNullable: true });
  // Base DN
  ldapBaseControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  // Server URI
  ldapUriControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  startTlsControl = new FormControl<boolean>(true, { nonNullable: true });
  tlsVersionControl = new FormControl<string>("TLSv1_3", { nonNullable: true });
  // Verify TLS certificate of the server.
  tlsVerifyControl = new FormControl<boolean>(true, { nonNullable: true });
  // CA Certificate
  tlsCaFileControl = new FormControl<string>("", { nonNullable: true });

  // --- Credentials ---
  bindTypeControl = new FormControl<BindType>("Simple", { nonNullable: true });
  bindPwControl = new FormControl<string>("", { nonNullable: true });
  bindDnControl = new FormControl<string>("", { nonNullable: true });

  // --- Settings ---
  timeoutControl = new FormControl<number>(5, { nonNullable: true });
  cacheTimeoutControl = new FormControl<number>(120, { nonNullable: true });
  sizeLimitControl = new FormControl<number>(500, { nonNullable: true });
  // Server Pool Retry Rounds
  serverPoolRoundsControl = new FormControl<number>(2, { nonNullable: true });
  // Server Pool Skip Timeout
  serverPoolSkipControl = new FormControl<number>(30, { nonNullable: true });
  // Per-Process Server Pool
  serverPoolPersistentControl = new FormControl<boolean>(false, { nonNullable: true });
  // Edit User Store
  editableControl = new FormControl<boolean>(false, { nonNullable: true });
  // Object Classes of a New Created User Object
  objectClassesControl = new FormControl<string>("", { nonNullable: true });
  // DN of a New Created User Object
  dnTemplateControl = new FormControl<string>("", { nonNullable: true });

  // --- Attributes & Mapping ---
  loginNameAttributeControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  uidTypeControl = new FormControl<string>("DN", { nonNullable: true });
  // Search Filter
  ldapSearchFilterControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  // Attribute Mapping
  userInfoControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  multivalueAttributesControl = new FormControl<string>("", { nonNullable: true });
  // Recursive Search of User Groups
  recursiveGroupSearchControl = new FormControl<boolean>(false, { nonNullable: true });
  // Base DN of User Groups
  groupBaseDNControl = new FormControl<string>("", { nonNullable: true });
  // Search Filter for User Groups
  groupSearchFilterControl = new FormControl<string>("", { nonNullable: true });
  groupNameAttributeControl = new FormControl<string>("", { nonNullable: true });
  // User Info Key
  groupAttributeMappingKeyControl = new FormControl<string>("", { nonNullable: true });
  // No Anonymous Referral Chasing
  noReferralsControl = new FormControl<boolean>(false, { nonNullable: true });
  // No Retrieval of Schema Information
  noSchemasControl = new FormControl<boolean>(false, { nonNullable: true });

  controls = computed<Record<string, AbstractControl>>(() => ({
    LDAPURI: this.ldapUriControl,
    START_TLS: this.startTlsControl,
    LDAPBASE: this.ldapBaseControl,
    LOGINNAMEATTRIBUTE: this.loginNameAttributeControl,
    LDAPSEARCHFILTER: this.ldapSearchFilterControl,
    USERINFO: this.userInfoControl,
    TLS_VERSION: this.tlsVersionControl,
    TLS_VERIFY: this.tlsVerifyControl,
    TLS_CA_FILE: this.tlsCaFileControl,
    SCOPE: this.scopeControl,
    AUTHTYPE: this.bindTypeControl,
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
    group_base_dn: this.groupBaseDNControl,
    group_search_filter: this.groupSearchFilterControl,
    group_name_attribute: this.groupNameAttributeControl,
    group_attribute_mapping_key: this.groupAttributeMappingKeyControl,
    NOREFERRALS: this.noReferralsControl,
    NOSCHEMAS: this.noSchemasControl
  }));

  constructor() {
    effect(() => {
      const initial = this.data();
      // --- Connection Details ---
      // Scope
      if (initial.SCOPE !== undefined) this.scopeControl.setValue(initial.SCOPE, { emitEvent: false });
      // Base DN
      if (initial.LDAPBASE !== undefined) this.ldapBaseControl.setValue(initial.LDAPBASE, { emitEvent: false });
      // Server URI
      if (initial.LDAPURI !== undefined) this.ldapUriControl.setValue(initial.LDAPURI, { emitEvent: false });
      // STARTTLS
      if (initial.START_TLS !== undefined)
        this.startTlsControl.setValue(parseBooleanValue(initial.START_TLS), { emitEvent: false });
      // TLS Version
      if (initial.TLS_VERSION !== undefined) this.tlsVersionControl.setValue(initial.TLS_VERSION, { emitEvent: false });
      // Verify TLS certificate of the server.
      if (initial.TLS_VERIFY !== undefined)
        this.tlsVerifyControl.setValue(parseBooleanValue(initial.TLS_VERIFY), { emitEvent: false });
      // CA Certificate
      if (initial.TLS_CA_FILE !== undefined) this.tlsCaFileControl.setValue(initial.TLS_CA_FILE, { emitEvent: false });

      // --- Credentials ---
      // Bind Type
      if (initial.AUTHTYPE !== undefined) this.bindTypeControl.setValue(initial.AUTHTYPE, { emitEvent: false });
      // Bind password / Keyfile Path
      if (initial.BINDPW !== undefined) this.bindPwControl.setValue(initial.BINDPW, { emitEvent: false });
      // Bind DN
      if (initial.BINDDN !== undefined) this.bindDnControl.setValue(initial.BINDDN, { emitEvent: false });

      // --- Settings ---
      // Timeout
      if (initial.TIMEOUT !== undefined) this.timeoutControl.setValue(Number(initial.TIMEOUT), { emitEvent: false });
      // Cache Timeout
      if (initial.CACHE_TIMEOUT !== undefined)
        this.cacheTimeoutControl.setValue(Number(initial.CACHE_TIMEOUT), { emitEvent: false });
      // Size Limit
      if (initial.SIZELIMIT !== undefined)
        this.sizeLimitControl.setValue(Number(initial.SIZELIMIT), { emitEvent: false });
      // Server Pool Retry Rounds
      if (initial.SERVERPOOL_ROUNDS !== undefined)
        this.serverPoolRoundsControl.setValue(Number(initial.SERVERPOOL_ROUNDS), { emitEvent: false });
      // Server Pool Skip Timeout
      if (initial.SERVERPOOL_SKIP !== undefined)
        this.serverPoolSkipControl.setValue(Number(initial.SERVERPOOL_SKIP), { emitEvent: false });
      // Per-Process Server Pool
      if (initial.SERVERPOOL_PERSISTENT !== undefined)
        this.serverPoolPersistentControl.setValue(parseBooleanValue(initial.SERVERPOOL_PERSISTENT), {
          emitEvent: false
        });
      // Edit User Store
      if (initial.EDITABLE !== undefined)
        this.editableControl.setValue(parseBooleanValue(initial.EDITABLE), { emitEvent: false });
      // Object Classes of a New Created User Object
      if (initial.OBJECT_CLASSES !== undefined)
        this.objectClassesControl.setValue(initial.OBJECT_CLASSES, { emitEvent: false });
      // DN of a New Created User Object
      if (initial.DN_TEMPLATE !== undefined) this.dnTemplateControl.setValue(initial.DN_TEMPLATE, { emitEvent: false });

      // --- Attributes & Mapping ---
      // Loginname Attribute
      if (initial.LOGINNAMEATTRIBUTE !== undefined)
        this.loginNameAttributeControl.setValue(initial.LOGINNAMEATTRIBUTE, { emitEvent: false });
      // UID Type
      if (initial.UIDTYPE !== undefined) this.uidTypeControl.setValue(initial.UIDTYPE, { emitEvent: false });
      // Search Filter
      if (initial.LDAPSEARCHFILTER !== undefined)
        this.ldapSearchFilterControl.setValue(initial.LDAPSEARCHFILTER, { emitEvent: false });
      // Attribute Mapping
      if (initial.USERINFO !== undefined) this.userInfoControl.setValue(initial.USERINFO, { emitEvent: false });
      // Multivalue Attributes
      if (initial.MULTIVALUEATTRIBUTES !== undefined)
        this.multivalueAttributesControl.setValue(initial.MULTIVALUEATTRIBUTES, { emitEvent: false });
      // Recursive Search of User Groups
      if (initial.recursive_group_search !== undefined)
        this.recursiveGroupSearchControl.setValue(parseBooleanValue(initial.recursive_group_search), {
          emitEvent: false
        });
      // Base DN of User Groups
      if (initial.group_base_dn !== undefined)
        this.groupBaseDNControl.setValue(initial.group_base_dn, { emitEvent: false });
      // Search Filter for User Groups
      if (initial.group_search_filter !== undefined)
        this.groupSearchFilterControl.setValue(initial.group_search_filter, { emitEvent: false });
      // Group Name Attribute
      if (initial.group_name_attribute !== undefined)
        this.groupNameAttributeControl.setValue(initial.group_name_attribute, { emitEvent: false });
      // User Info Key
      if (initial.group_attribute_mapping_key !== undefined)
        this.groupAttributeMappingKeyControl.setValue(initial.group_attribute_mapping_key, { emitEvent: false });
      // No Anonymous Referral Chasing
      if (initial.NOREFERRALS !== undefined)
        this.noReferralsControl.setValue(parseBooleanValue(initial.NOREFERRALS), { emitEvent: false });
      // No Retrieval of Schema Information
      if (initial.NOSCHEMAS !== undefined)
        this.noSchemasControl.setValue(parseBooleanValue(initial.NOSCHEMAS), { emitEvent: false });
      this._updateTlsLogic();
    });

    merge(this.startTlsControl.valueChanges, this.tlsVerifyControl.valueChanges, this.ldapUriControl.valueChanges)
      .pipe(takeUntilDestroyed())
      .subscribe(() => this._updateTlsLogic());
  }

  private _updateTlsLogic(): void {
    if (this._isLdaps) {
      this.startTlsControl.setValue(true, { emitEvent: false });
      this.startTlsControl.disable({ emitEvent: false });
    } else {
      this.startTlsControl.enable({ emitEvent: false });
    }

    const startTls = this.startTlsControl.value;
    const tlsVerify = this.tlsVerifyControl.value;

    if (!startTls) {
      this.tlsVersionControl.disable({ emitEvent: false });
      this.tlsVerifyControl.disable({ emitEvent: false });
    } else {
      this.tlsVersionControl.enable({ emitEvent: false });
      this.tlsVerifyControl.enable({ emitEvent: false });
    }

    if (!startTls || !tlsVerify) {
      this.tlsCaFileControl.disable({ emitEvent: false });
      this.tlsCaFileControl.clearValidators();
    } else {
      this.tlsCaFileControl.enable({ emitEvent: false });
      this.tlsCaFileControl.setValidators([Validators.required]);
    }

    this.tlsCaFileControl.updateValueAndValidity({ emitEvent: false });
  }

  applyLdapPreset(preset: LdapPreset): void {
    this.loginNameAttributeControl.setValue(preset.loginName);
    this.ldapSearchFilterControl.setValue(preset.searchFilter);
    this.userInfoControl.setValue(preset.userInfo);
    this.uidTypeControl.setValue(preset.uidType);
    this.multivalueAttributesControl.setValue("");
  }

  get showTls(): boolean {
    return this._isLdap || this._isLdaps;
  }

  private get _isLdap(): boolean {
    return (this.ldapUriControl.value || "").startsWith("ldap:");
  }

  private get _isLdaps(): boolean {
    return (this.ldapUriControl.value || "").startsWith("ldaps:");
  }
}
