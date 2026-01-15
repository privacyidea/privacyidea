import { Component, computed, effect, inject, input } from "@angular/core";
import { AbstractControl, FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatOption } from "@angular/material/core";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatButtonModule } from "@angular/material/button";
import { LDAPResolverData, ResolverService } from "../../../../services/resolver/resolver.service";

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
    MatButtonModule
  ],
  templateUrl: "./ldap-resolver.component.html",
  styleUrl: "./ldap-resolver.component.scss"
})
export class LdapResolverComponent {
  private readonly resolverService = inject(ResolverService);

  data = input<Partial<LDAPResolverData>>({});

  isEditMode = computed(() => !!this.resolverService.selectedResolverName());

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

  ldapUriControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  ldapBaseControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  loginNameAttributeControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  ldapSearchFilterControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  userInfoControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });

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

  applyLdapPreset(preset: any): void {
    this.loginNameAttributeControl.setValue(preset.loginName);
    this.ldapSearchFilterControl.setValue(preset.searchFilter);
    this.userInfoControl.setValue(preset.userInfo);
    this.uidTypeControl.setValue(preset.uidType);
    this.multivalueAttributesControl.setValue("");
  }

  constructor() {
    effect(() => {
      const initial = this.data();
      if (initial.LDAPURI !== undefined) this.ldapUriControl.setValue(initial.LDAPURI, { emitEvent: false });
      if (initial.LDAPBASE !== undefined) this.ldapBaseControl.setValue(initial.LDAPBASE, { emitEvent: false });
      if (initial.LOGINNAMEATTRIBUTE !== undefined) this.loginNameAttributeControl.setValue(initial.LOGINNAMEATTRIBUTE, { emitEvent: false });
      if (initial.LDAPSEARCHFILTER !== undefined) this.ldapSearchFilterControl.setValue(initial.LDAPSEARCHFILTER, { emitEvent: false });
      if (initial.USERINFO !== undefined) this.userInfoControl.setValue(initial.USERINFO, { emitEvent: false });

      if (initial.TLS_VERSION !== undefined) this.tlsVersionControl.setValue(initial.TLS_VERSION, { emitEvent: false });
      if (initial.TLS_VERIFY !== undefined) this.tlsVerifyControl.setValue(initial.TLS_VERIFY, { emitEvent: false });
      if (initial.TLS_CA_FILE !== undefined) this.tlsCaFileControl.setValue(initial.TLS_CA_FILE, { emitEvent: false });
      if (initial.SCOPE !== undefined) this.scopeControl.setValue(initial.SCOPE, { emitEvent: false });
      if (initial.AUTHTYPE !== undefined) this.authTypeControl.setValue(initial.AUTHTYPE, { emitEvent: false });
      if (initial.BINDDN !== undefined) this.bindDnControl.setValue(initial.BINDDN, { emitEvent: false });
      if (initial.BINDPW !== undefined) this.bindPwControl.setValue(initial.BINDPW, { emitEvent: false });
      if (initial.TIMEOUT !== undefined) this.timeoutControl.setValue(initial.TIMEOUT, { emitEvent: false });
      if (initial.CACHE_TIMEOUT !== undefined) this.cacheTimeoutControl.setValue(initial.CACHE_TIMEOUT, { emitEvent: false });
      if (initial.SIZELIMIT !== undefined) this.sizeLimitControl.setValue(initial.SIZELIMIT, { emitEvent: false });
      if (initial.SERVERPOOL_ROUNDS !== undefined) this.serverPoolRoundsControl.setValue(initial.SERVERPOOL_ROUNDS, { emitEvent: false });
      if (initial.SERVERPOOL_SKIP !== undefined) this.serverPoolSkipControl.setValue(initial.SERVERPOOL_SKIP, { emitEvent: false });
      if (initial.SERVERPOOL_PERSISTENT !== undefined) this.serverPoolPersistentControl.setValue(initial.SERVERPOOL_PERSISTENT, { emitEvent: false });
      if (initial.EDITABLE !== undefined) this.editableControl.setValue(initial.EDITABLE, { emitEvent: false });
      if (initial.OBJECT_CLASSES !== undefined) this.objectClassesControl.setValue(initial.OBJECT_CLASSES, { emitEvent: false });
      if (initial.DN_TEMPLATE !== undefined) this.dnTemplateControl.setValue(initial.DN_TEMPLATE, { emitEvent: false });
      if (initial.MULTIVALUEATTRIBUTES !== undefined) this.multivalueAttributesControl.setValue(initial.MULTIVALUEATTRIBUTES, { emitEvent: false });
      if (initial.UIDTYPE !== undefined) this.uidTypeControl.setValue(initial.UIDTYPE, { emitEvent: false });
      if (initial.recursive_group_search !== undefined) this.recursiveGroupSearchControl.setValue(initial.recursive_group_search, { emitEvent: false });
      if (initial.group_search_filter !== undefined) this.groupSearchFilterControl.setValue(initial.group_search_filter, { emitEvent: false });
      if (initial.group_name_attribute !== undefined) this.groupNameAttributeControl.setValue(initial.group_name_attribute, { emitEvent: false });
      if (initial.group_attribute_mapping_key !== undefined) this.groupAttributeMappingKeyControl.setValue(initial.group_attribute_mapping_key, { emitEvent: false });
      if (initial.NOREFERRALS !== undefined) this.noReferralsControl.setValue(initial.NOREFERRALS, { emitEvent: false });
      if (initial.NOSCHEMAS !== undefined) this.noSchemasControl.setValue(initial.NOSCHEMAS, { emitEvent: false });
    });
  }
}
