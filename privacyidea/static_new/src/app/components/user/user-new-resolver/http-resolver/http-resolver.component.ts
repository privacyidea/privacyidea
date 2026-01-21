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
import { Component, computed, effect, input, linkedSignal, signal } from "@angular/core";
import { AbstractControl, FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { toSignal } from "@angular/core/rxjs-interop";

import { MatFormField, MatHint, MatInput, MatLabel } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatTableModule } from "@angular/material/table";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";

import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatDivider } from "@angular/material/list";
import { MatError } from "@angular/material/form-field";
import { MatButtonToggle, MatButtonToggleGroup } from "@angular/material/button-toggle";
import { HttpConfigComponent } from "./http-config/http-config.component";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { parseBooleanValue } from "../../../../utils/parse-boolean-value";

export type AttributeMappingRow = {
  privacyideaAttr: string | null;
  userStoreAttr: string;
  isCustom?: boolean;
};

@Component({
  selector: "app-http-resolver",
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    MatFormField,
    MatLabel,
    MatError,
    MatInput,
    MatSelect,
    MatOption,
    MatCheckbox,
    MatHint,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatDivider,
    MatButtonToggleGroup,
    MatButtonToggle,
    HttpConfigComponent,
    ClearableInputComponent
  ],
  templateUrl: "./http-resolver.component.html",
  styleUrl: "./http-resolver.component.scss"
})
export class HttpResolverComponent {
  protected readonly privacyideaAttributes: string[] = [
    "userid",
    "givenname",
    "username",
    "email",
    "surname",
    "phone",
    "mobile"
  ];
  protected readonly displayedColumns: string[] = ["privacyideaAttr", "userStoreAttr", "actions"];
  protected readonly CUSTOM_ATTR_VALUE = "__custom__";
  data = input<any>({});
  type = input<string>("httpresolver");
  isAdvanced: boolean = false;
  isAuthorizationExpanded: boolean = false;
  endpointControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  methodControl = new FormControl<string>("GET", { nonNullable: true, validators: [Validators.required] });
  requestMappingControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  headersControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  responseMappingControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  errorResponseControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  baseUrlControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  tenantControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  clientIdControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  clientSecretControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });

  realmControl = new FormControl<string>("", { nonNullable: true });
  globalHeadersControl = new FormControl<string>("", { nonNullable: true });
  editableControl = new FormControl<boolean>(false, { nonNullable: true });
  verifyTlsControl = new FormControl<boolean>(true, { nonNullable: true });
  tlsCaPathControl = new FormControl<string>("", { nonNullable: true });
  timeoutControl = new FormControl<number>(60, { nonNullable: true });
  usernameControl = new FormControl<string>("", { nonNullable: true });
  passwordControl = new FormControl<string>("", { nonNullable: true });
  authorityControl = new FormControl<string>("", { nonNullable: true });
  clientCredentialTypeControl = new FormControl<string>("secret", { nonNullable: true });
  clientCredentialType = toSignal(this.clientCredentialTypeControl.valueChanges, { initialValue: this.clientCredentialTypeControl.value });

  clientCertificateGroup = new FormGroup({
    private_key_file: new FormControl<string>("", { nonNullable: true }),
    private_key_password: new FormControl<string>("", { nonNullable: true }),
    certificate_fingerprint: new FormControl<string>("", { nonNullable: true })
  });

  attributeMappingControl = new FormControl<Record<string, string>>({}, { nonNullable: true });

  configAuthorizationGroup = this.createConfigGroup();
  configUserAuthGroup = this.createConfigGroup();
  configGetUserListGroup = this.createConfigGroup();
  configGetUserByIdGroup = this.createConfigGroup();
  configGetUserByNameGroup = this.createConfigGroup();
  configCreateUserGroup = this.createConfigGroup();
  configEditUserGroup = this.createConfigGroup();
  configDeleteUserGroup = this.createConfigGroup();

  checkUserPasswordHint = computed(() => {
    if (this.type() === "entraidresolver") {
      return $localize`Possible tags: ` + `{userid} {username} {password} {client_id} {client_credential} {tenant}`;
    }
    return $localize`Possible tags: \` + \` {userid} {username} {password}`;
  });

  protected basicSettings = linkedSignal<boolean>(() => {
    if (this.isAdvanced) {
      return false;
    }
    return this.data().base_url === undefined;
  });
  controls = computed<Record<string, AbstractControl>>(() => {
    const controls: Record<string, AbstractControl> = {};
    const data = this.data();

    if (!this.isAdvanced && this.basicSettings()) {
      controls["endpoint"] = this.endpointControl;
      controls["method"] = this.methodControl;
      controls["requestMapping"] = this.requestMappingControl;
      controls["headers"] = this.headersControl;
      controls["responseMapping"] = this.responseMappingControl;

      if (data?.hasSpecialErrorHandler) {
        controls["errorResponse"] = this.errorResponseControl;
      }
    } else {
      controls["base_url"] = this.baseUrlControl;
      controls["realm"] = this.realmControl;
      controls["headers"] = this.globalHeadersControl;
      controls["Editable"] = this.editableControl;
      controls["verify_tls"] = this.verifyTlsControl;
      controls["tls_ca_path"] = this.tlsCaPathControl;
      controls["timeout"] = this.timeoutControl;
      controls["attribute_mapping"] = this.attributeMappingControl;

      controls["config_authorization"] = this.configAuthorizationGroup;
      controls["config_user_auth"] = this.configUserAuthGroup;
      controls["config_get_user_list"] = this.configGetUserListGroup;
      controls["config_get_user_by_id"] = this.configGetUserByIdGroup;
      controls["config_get_user_by_name"] = this.configGetUserByNameGroup;
      controls["config_create_user"] = this.configCreateUserGroup;
      controls["config_edit_user"] = this.configEditUserGroup;
      controls["config_delete_user"] = this.configDeleteUserGroup;

      if (this.type() === "entraidresolver") {
        controls["tenant"] = this.tenantControl;
        controls["client_id"] = this.clientIdControl;
        controls["authority"] = this.authorityControl;
        controls["client_credential_type"] = this.clientCredentialTypeControl;
        controls["client_certificate"] = this.clientCertificateGroup;

        if (this.clientCredentialType() === "secret") {
          controls["client_secret"] = this.clientSecretControl;
        }
      } else {
        controls["username"] = this.usernameControl;
        controls["password"] = this.passwordControl;
      }
    }
    return controls;
  });
  protected defaultMapping = signal<AttributeMappingRow[]>([
    { privacyideaAttr: "userid", userStoreAttr: "userid" },
    { privacyideaAttr: "givenname", userStoreAttr: "givenname" }
  ]);
  protected mappingRows = linkedSignal<AttributeMappingRow[]>(() => {
    const existing = this.data()?.attribute_mapping;
    let rows: AttributeMappingRow[] = [];
    if (existing && Object.keys(existing).length > 0) {
      rows = Object.entries(existing).map(([privacyideaAttr, userStoreAttr]) => ({
        privacyideaAttr,
        userStoreAttr: userStoreAttr as string,
        isCustom: !this.privacyideaAttributes.includes(privacyideaAttr)
      }));
    } else {
      rows = this.defaultMapping().map(row => ({ ...row, isCustom: false }));
    }
    // Always add an empty row at the end to allow adding new attributes
    rows.push({ privacyideaAttr: null, userStoreAttr: "", isCustom: false });
    return rows;
  });
  protected availableAttributes = computed(() => {
    const rows = this.mappingRows();
    return rows.map((_, rowIndex) => {
      const selectedAttributes = rows
        .filter((_, i) => i !== rowIndex)
        .map(row => row.privacyideaAttr);
      return this.privacyideaAttributes.filter(attr => !selectedAttributes.includes(attr));
    });
  });

  constructor() {
    effect(() => {
      this.syncControls();
    });

    effect(() => {
      const basic = this.basicSettings();
      if (!basic && !this.responseMappingControl.value) {
        this.responseMappingControl.setValue("{\"username\":\"{username}\", \"userid\":\"{userid}\"}");
        this.verifyTlsControl.setValue(true);
      }
      if (basic && this.responseMappingControl.value) {
        this.responseMappingControl.setValue("");
        this.verifyTlsControl.setValue(false);
      }
    });
  }

  setCustomAttr(rowIndex: number, customValue: string): void {
    const v = (customValue ?? "").trim();
    const rows = [...this.mappingRows()];
    rows[rowIndex].privacyideaAttr = v;
    this.mappingRows.set(rows);
    this.onMappingChanged();
  }

  onPrivacyIdeaAttrChanged(rowIndex: number, value: string | null): void {
    const rows = [...this.mappingRows()];
    const row = rows[rowIndex];

    if (value === this.CUSTOM_ATTR_VALUE) {
      row.isCustom = true;
      row.privacyideaAttr = "";
      if (rowIndex === rows.length - 1) {
        rows.push({ privacyideaAttr: null, userStoreAttr: "", isCustom: false });
      }
      this.mappingRows.set(rows);
      this.onMappingChanged();
      return;
    }

    row.isCustom = false;
    row.privacyideaAttr = value;

    if (rowIndex === rows.length - 1 && value !== null) {
      rows.push({ privacyideaAttr: null, userStoreAttr: "", isCustom: false });
    }
    this.mappingRows.set(rows);
    this.onMappingChanged();
  }


  removeMappingRow(index: number): void {
    this.mappingRows.update(rows => {
      const newRows = rows.filter((_, i) => i !== index);
      if (newRows.length === 0 || newRows[newRows.length - 1].privacyideaAttr !== null || newRows[newRows.length - 1].isCustom) {
        newRows.push({ privacyideaAttr: null, userStoreAttr: "", isCustom: false });
      }
      return newRows;
    });
    this.syncMappingToData();
  }

  protected createConfigGroup() {
    return new FormGroup({
      method: new FormControl<string>("GET", { nonNullable: true }),
      endpoint: new FormControl<string>("", { nonNullable: true }),
      headers: new FormControl<string>("", { nonNullable: true }),
      requestMapping: new FormControl<string>("", { nonNullable: true }),
      responseMapping: new FormControl<string>("", { nonNullable: true }),
      hasSpecialErrorHandler: new FormControl<boolean>(false, { nonNullable: true }),
      errorResponse: new FormControl<string>("", { nonNullable: true })
    });
  }

  protected syncControls(): void {
    const data = this.data();
    if (!data) return;

    if (data.endpoint !== undefined) this.endpointControl.setValue(data.endpoint, { emitEvent: false });
    if (data.method !== undefined) this.methodControl.setValue(data.method, { emitEvent: false });
    if (data.requestMapping !== undefined) this.requestMappingControl.setValue(data.requestMapping, { emitEvent: false });
    if (data.headers !== undefined) this.headersControl.setValue(data.headers, { emitEvent: false });
    if (data.responseMapping !== undefined) this.responseMappingControl.setValue(data.responseMapping, { emitEvent: false });
    if (data.errorResponse !== undefined) this.errorResponseControl.setValue(data.errorResponse, { emitEvent: false });
    if (data.base_url !== undefined) this.baseUrlControl.setValue(data.base_url, { emitEvent: false });
    if (data.tenant !== undefined) this.tenantControl.setValue(data.tenant, { emitEvent: false });
    if (data.client_id !== undefined) this.clientIdControl.setValue(data.client_id, { emitEvent: false });
    if (data.client_secret !== undefined) this.clientSecretControl.setValue(data.client_secret, { emitEvent: false });

    if (data.realm !== undefined) this.realmControl.setValue(data.realm, { emitEvent: false });
    if (data.headers !== undefined) this.globalHeadersControl.setValue(data.headers, { emitEvent: false });
    if (data.Editable !== undefined) this.editableControl.setValue(parseBooleanValue(data.Editable), { emitEvent: false });
    if (data.verify_tls !== undefined) this.verifyTlsControl.setValue(parseBooleanValue(data.verify_tls), { emitEvent: false });
    if (data.tls_ca_path !== undefined) this.tlsCaPathControl.setValue(data.tls_ca_path, { emitEvent: false });
    if (data.timeout !== undefined) this.timeoutControl.setValue(Number(data.timeout), { emitEvent: false });
    if (data.username !== undefined) this.usernameControl.setValue(data.username, { emitEvent: false });
    if (data.password !== undefined) this.passwordControl.setValue(data.password, { emitEvent: false });
    if (data.authority !== undefined) this.authorityControl.setValue(data.authority, { emitEvent: false });
    if (data.client_credential_type !== undefined) this.clientCredentialTypeControl.setValue(data.client_credential_type, { emitEvent: false });

    if (data.client_certificate) {
      this.clientCertificateGroup.patchValue(data.client_certificate, { emitEvent: false });
    }

    if (data.attribute_mapping) {
      this.attributeMappingControl.setValue(data.attribute_mapping, { emitEvent: false });
    } else {
      this.syncMappingToData();
    }

    this.syncGroup(this.configAuthorizationGroup, data.config_authorization);
    this.syncGroup(this.configUserAuthGroup, data.config_user_auth);
    this.syncGroup(this.configGetUserListGroup, data.config_get_user_list);
    this.syncGroup(this.configGetUserByIdGroup, data.config_get_user_by_id);
    this.syncGroup(this.configGetUserByNameGroup, data.config_get_user_by_name);
    this.syncGroup(this.configCreateUserGroup, data.config_create_user);
    this.syncGroup(this.configEditUserGroup, data.config_edit_user);
    this.syncGroup(this.configDeleteUserGroup, data.config_delete_user);
  }

  protected syncGroup(group: FormGroup, config: any) {
    if (config) {
      group.patchValue(config, { emitEvent: false });
    }
  }

  protected onMappingChanged(): void {
    this.mappingRows.set([...this.mappingRows()]);
    this.syncMappingToData();
  }

  private syncMappingToData(): void {
    const map: Record<string, string> = {};

    for (const row of this.mappingRows()) {
      const k = (row.privacyideaAttr ?? "").trim();
      const v = (row.userStoreAttr ?? "").trim();
      if (k && v) {
        map[k] = v;
      }
    }

    this.attributeMappingControl.setValue(map);
  }
}
