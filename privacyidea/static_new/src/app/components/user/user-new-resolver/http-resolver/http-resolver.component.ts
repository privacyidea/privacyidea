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
import { Component, computed, effect, inject, input, linkedSignal, signal } from "@angular/core";
import { form, FormField, required } from "@angular/forms/signals";

import { MatButtonModule } from "@angular/material/button";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatIconModule } from "@angular/material/icon";
import { MatFormField, MatHint, MatInput, MatLabel } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatTableModule } from "@angular/material/table";

import { MatButtonToggle, MatButtonToggleGroup } from "@angular/material/button-toggle";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatError } from "@angular/material/form-field";
import { MatDivider } from "@angular/material/list";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ResolverService } from "@services/resolver/resolver.service";
import { parseBooleanValue } from "@utils/parse-boolean-value";
import { HttpConfigComponent, HttpConfigModel } from "./http-config/http-config.component";
import { HttpGroupsAttributeComponent, UserGroupsModel } from "./http-groups-attribute/http-groups-attribute.component";

export type AttributeMappingRow = {
  privacyideaAttr: string | null;
  userStoreAttr: string;
  isCustom?: boolean;
};

export interface ClientCertificateModel {
  private_key_file: string;
  private_key_password: string;
  certificate_fingerprint: string;
}

export interface HttpResolverModel {
  // Basic mode fields
  endpoint: string;
  method: string;
  requestMapping: string;
  headers: string;
  responseMapping: string;
  errorResponse: string;
  // Advanced mode fields
  base_url: string;
  realm: string;
  global_headers: string;
  Editable: boolean;
  verify_tls: boolean;
  tls_ca_path: string;
  timeout: number;
  // Auth fields (non-entraid)
  username: string;
  password: string;
  // Entraid fields
  tenant: string;
  client_id: string;
  authority: string;
  client_credential_type: string;
  client_secret: string;
  client_certificate: ClientCertificateModel;
  // Nested config groups
  config_authorization: HttpConfigModel;
  config_user_auth: HttpConfigModel;
  config_get_user_list: HttpConfigModel;
  config_get_user_by_id: HttpConfigModel;
  config_get_user_by_name: HttpConfigModel;
  config_create_user: HttpConfigModel;
  config_edit_user: HttpConfigModel;
  config_delete_user: HttpConfigModel;
  config_get_user_groups: UserGroupsModel;
  attribute_mapping: Record<string, string>;
}

const EMPTY_HTTP_CONFIG: HttpConfigModel = {
  method: "GET",
  endpoint: "",
  headers: "",
  requestMapping: "",
  responseMapping: "",
  hasSpecialErrorHandler: false,
  errorResponse: ""
};

const EMPTY_USER_GROUPS: UserGroupsModel = {
  active: false,
  pi_user_groups_key: "groups",
  user_groups_attribute: "",
  method: "GET",
  endpoint: ""
};

function emptyHttpModel(): HttpResolverModel {
  return {
    endpoint: "",
    method: "GET",
    requestMapping: "",
    headers: "",
    responseMapping: "",
    errorResponse: "",
    base_url: "",
    realm: "",
    global_headers: "",
    Editable: false,
    verify_tls: true,
    tls_ca_path: "",
    timeout: 60,
    username: "",
    password: "",
    tenant: "",
    client_id: "",
    authority: "",
    client_credential_type: "secret",
    client_secret: "",
    client_certificate: {
      private_key_file: "",
      private_key_password: "",
      certificate_fingerprint: ""
    },
    config_authorization: { ...EMPTY_HTTP_CONFIG },
    config_user_auth: { ...EMPTY_HTTP_CONFIG },
    config_get_user_list: { ...EMPTY_HTTP_CONFIG },
    config_get_user_by_id: { ...EMPTY_HTTP_CONFIG },
    config_get_user_by_name: { ...EMPTY_HTTP_CONFIG },
    config_create_user: { ...EMPTY_HTTP_CONFIG },
    config_edit_user: { ...EMPTY_HTTP_CONFIG },
    config_delete_user: { ...EMPTY_HTTP_CONFIG },
    config_get_user_groups: { ...EMPTY_USER_GROUPS },
    attribute_mapping: {}
  };
}

@Component({
  selector: "app-http-resolver",
  standalone: true,
  imports: [
    FormField,
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
    ClearableInputComponent,
    HttpGroupsAttributeComponent
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
  private resolverService = inject(ResolverService);
  data = input({});
  type = input<string>("httpresolver");
  serverDefaults = signal<any>({});
  mergedData = computed(() => {
    const data = this.data();
    if (data && Object.keys(data).length > 0) {
      return data;
    }
    return this.serverDefaults();
  });
  isAdvanced: boolean = false;
  isAuthorizationExpanded: boolean = false;

  model = signal<HttpResolverModel>(emptyHttpModel());

  httpForm = form(this.model, (f) => {
    // Validators applied conditionally in template, but form-level validation
    // is handled via isValid() which checks required fields based on mode
  });

  // Expose nested sub-signals for sub-components
  configAuthorizationModel = computed(() => {
    const currentModel = this.model();
    return {
      get: () => currentModel.config_authorization,
      update: (fn: (config: HttpConfigModel) => HttpConfigModel) => {
        this.model.update(model => ({ ...model, config_authorization: fn(model.config_authorization) }));
      }
    } as any;
  });

  isValid = () => {
    const currentModel = this.model();
    const basic = this.basicSettings();
    if (!basic && this.isAdvanced) {
      return !!currentModel.base_url;
    }
    if (basic) {
      return !!currentModel.endpoint && !!currentModel.method && !!currentModel.requestMapping && !!currentModel.headers && !!currentModel.responseMapping;
    }
    return !!currentModel.base_url;
  };
  isDirty = () => this.httpForm().dirty();
  getValue = () => this.model();

  checkUserPasswordHint = computed(() => {
    if (this.type() === "entraidresolver") {
      return $localize`Possible tags: ` + `{userid} {username} {password} {client_id} {client_credential} {tenant}`;
    }
    return $localize`Possible tags: ` + `{userid} {username} {password}`;
  });

  protected basicSettings = linkedSignal<boolean>(() => {
    if (this.isAdvanced) {
      return false;
    }
    return (this.mergedData() as any).base_url === undefined;
  });

  // Signals derived from model for reactive sub-component inputs
  configAuthModel = signal<HttpConfigModel>({ ...EMPTY_HTTP_CONFIG });
  configUserAuthModel = signal<HttpConfigModel>({ ...EMPTY_HTTP_CONFIG });
  configGetUserListModel = signal<HttpConfigModel>({ ...EMPTY_HTTP_CONFIG });
  configGetUserByIdModel = signal<HttpConfigModel>({ ...EMPTY_HTTP_CONFIG });
  configGetUserByNameModel = signal<HttpConfigModel>({ ...EMPTY_HTTP_CONFIG });
  configCreateUserModel = signal<HttpConfigModel>({ ...EMPTY_HTTP_CONFIG });
  configEditUserModel = signal<HttpConfigModel>({ ...EMPTY_HTTP_CONFIG });
  configDeleteUserModel = signal<HttpConfigModel>({ ...EMPTY_HTTP_CONFIG });
  userGroupsModel = signal<UserGroupsModel>({ ...EMPTY_USER_GROUPS });

  protected defaultMapping = signal<AttributeMappingRow[]>([
    { privacyideaAttr: "userid", userStoreAttr: "userid" },
    { privacyideaAttr: "givenname", userStoreAttr: "givenname" }
  ]);
  protected mappingRows = linkedSignal<AttributeMappingRow[]>(() => {
    const existing = (this.mergedData() as any)?.attribute_mapping;
    let rows: AttributeMappingRow[] = [];
    if (existing && Object.keys(existing).length > 0) {
      rows = Object.entries(existing).map(([privacyideaAttr, userStoreAttr]) => ({
        privacyideaAttr,
        userStoreAttr: userStoreAttr as string,
        isCustom: !this.privacyideaAttributes.includes(privacyideaAttr)
      }));
    } else {
      rows = this.defaultMapping().map((row) => ({ ...row, isCustom: false }));
    }
    // Always add an empty row at the end to allow adding new attributes
    rows.push({ privacyideaAttr: null, userStoreAttr: "", isCustom: false });
    return rows;
  });
  protected availableAttributes = computed(() => {
    const rows = this.mappingRows();
    return rows.map((_, rowIndex) => {
      const selectedAttributes = rows.filter((_, i) => i !== rowIndex).map((row) => row.privacyideaAttr);
      return this.privacyideaAttributes.filter((attr) => !selectedAttributes.includes(attr));
    });
  });

  constructor() {
    effect(() => {
      this.syncControls();
    });

    effect(
      () => {
        if (Object.keys(this.data()).length === 0) {
          this.resolverService.getDefaultResolverConfig(this.type()).subscribe((resp) => {
            if (resp.result?.status && resp.result?.value) {
              this.serverDefaults.set(resp.result.value);
            }
          });
        }
      },
      { allowSignalWrites: true }
    );

    effect(() => {
      const basic = this.basicSettings();
      const data = this.mergedData() as any;
      if (!basic && !this.model().responseMapping) {
        if (data.responseMapping === undefined) {
          this.model.update(m => ({ ...m, responseMapping: '{"username":"{username}", "userid":"{userid}"}' }));
        }
        if (data.verify_tls === undefined) {
          this.model.update(m => ({ ...m, verify_tls: true }));
        }
      }
      if (basic && this.model().responseMapping) {
        if (data.responseMapping === undefined) {
          this.model.update(m => ({ ...m, responseMapping: "" }));
        }
        if (data.verify_tls === undefined) {
          this.model.update(m => ({ ...m, verify_tls: false }));
        }
      }
    });

    // Sync sub-component models to main model when they change
    effect(() => {
      const auth = this.configAuthModel();
      this.model.update(m => ({ ...m, config_authorization: auth }));
    });
    effect(() => {
      const userAuth = this.configUserAuthModel();
      this.model.update(m => ({ ...m, config_user_auth: userAuth }));
    });
    effect(() => {
      const list = this.configGetUserListModel();
      this.model.update(m => ({ ...m, config_get_user_list: list }));
    });
    effect(() => {
      const byId = this.configGetUserByIdModel();
      this.model.update(m => ({ ...m, config_get_user_by_id: byId }));
    });
    effect(() => {
      const byName = this.configGetUserByNameModel();
      this.model.update(m => ({ ...m, config_get_user_by_name: byName }));
    });
    effect(() => {
      const create = this.configCreateUserModel();
      this.model.update(m => ({ ...m, config_create_user: create }));
    });
    effect(() => {
      const edit = this.configEditUserModel();
      this.model.update(m => ({ ...m, config_edit_user: edit }));
    });
    effect(() => {
      const del = this.configDeleteUserModel();
      this.model.update(m => ({ ...m, config_delete_user: del }));
    });
    effect(() => {
      const groups = this.userGroupsModel();
      this.model.update(m => ({ ...m, config_get_user_groups: groups }));
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
    this.mappingRows.update((rows) => {
      const newRows = rows.filter((_, i) => i !== index);
      if (
        newRows.length === 0 ||
        newRows[newRows.length - 1].privacyideaAttr !== null ||
        newRows[newRows.length - 1].isCustom
      ) {
        newRows.push({ privacyideaAttr: null, userStoreAttr: "", isCustom: false });
      }
      return newRows;
    });
    this.syncMappingToData();
  }

  protected syncControls(): void {
    const data = this.mergedData() as any;
    if (!data) return;

    const updates: Partial<HttpResolverModel> = {};

    if (data.endpoint !== undefined) updates.endpoint = data.endpoint;
    if (data.method !== undefined) updates.method = data.method.toUpperCase();
    if (data.requestMapping !== undefined) updates.requestMapping = this.formatConfigValue(data.requestMapping);
    if (data.headers !== undefined) updates.headers = this.formatConfigValue(data.headers);
    if (data.responseMapping !== undefined) updates.responseMapping = this.formatConfigValue(data.responseMapping);
    if (data.errorResponse !== undefined) updates.errorResponse = this.formatConfigValue(data.errorResponse);
    if (data.base_url !== undefined) updates.base_url = data.base_url;
    if (data.tenant !== undefined) updates.tenant = data.tenant;
    if (data.client_id !== undefined) updates.client_id = data.client_id;
    if (data.client_secret !== undefined) updates.client_secret = data.client_secret;
    if (data.realm !== undefined) updates.realm = data.realm;
    if (data.headers !== undefined) updates.global_headers = this.formatConfigValue(data.headers);
    if (data.Editable !== undefined) updates.Editable = parseBooleanValue(data.Editable);
    if (data.verify_tls !== undefined) updates.verify_tls = parseBooleanValue(data.verify_tls);
    if (data.tls_ca_path !== undefined) updates.tls_ca_path = data.tls_ca_path;
    if (data.timeout !== undefined) updates.timeout = Number(data.timeout);
    if (data.username !== undefined) updates.username = data.username;
    if (data.password !== undefined) updates.password = data.password;
    if (data.authority !== undefined) updates.authority = data.authority;
    if (data.client_credential_type !== undefined) updates.client_credential_type = data.client_credential_type;

    if (data.client_certificate) {
      updates.client_certificate = {
        private_key_file: data.client_certificate.private_key_file || "",
        private_key_password: data.client_certificate.private_key_password || "",
        certificate_fingerprint: data.client_certificate.certificate_fingerprint || ""
      };
    }

    if (data.attribute_mapping) {
      updates.attribute_mapping = data.attribute_mapping;
    } else {
      this.syncMappingToData();
    }

    if (Object.keys(updates).length > 0) {
      this.model.update(m => ({ ...m, ...updates }));
    }

    if (data.config_get_user_groups) {
      this.userGroupsModel.update(g => ({ ...g, ...this.sanitizeConfig(data.config_get_user_groups) }));
    }
    if (data.config_authorization) {
      this.configAuthModel.update(c => ({ ...c, ...this.sanitizeConfig(data.config_authorization) }));
    }
    if (data.config_user_auth) {
      this.configUserAuthModel.update(c => ({ ...c, ...this.sanitizeConfig(data.config_user_auth) }));
    }
    if (data.config_get_user_list) {
      this.configGetUserListModel.update(c => ({ ...c, ...this.sanitizeConfig(data.config_get_user_list) }));
    }
    if (data.config_get_user_by_id) {
      this.configGetUserByIdModel.update(c => ({ ...c, ...this.sanitizeConfig(data.config_get_user_by_id) }));
    }
    if (data.config_get_user_by_name) {
      this.configGetUserByNameModel.update(c => ({ ...c, ...this.sanitizeConfig(data.config_get_user_by_name) }));
    }
    if (data.config_create_user) {
      this.configCreateUserModel.update(c => ({ ...c, ...this.sanitizeConfig(data.config_create_user) }));
    }
    if (data.config_edit_user) {
      this.configEditUserModel.update(c => ({ ...c, ...this.sanitizeConfig(data.config_edit_user) }));
    }
    if (data.config_delete_user) {
      this.configDeleteUserModel.update(c => ({ ...c, ...this.sanitizeConfig(data.config_delete_user) }));
    }

    this.httpForm().reset();
  }

  private sanitizeConfig(config: any): any {
    const sanitized = { ...config };
    if (sanitized.method) {
      sanitized.method = sanitized.method.toUpperCase();
    }
    ["headers", "requestMapping", "responseMapping", "errorResponse"].forEach((field) => {
      if (sanitized[field] !== undefined) {
        sanitized[field] = this.formatConfigValue(sanitized[field]);
      }
    });
    return sanitized;
  }

  private formatConfigValue(value: {} | null): string {
    if (typeof value === "object" && value !== null) {
      if (Object.keys(value).length === 0) {
        return "";
      }
      return JSON.stringify(value);
    }
    return <string>value ?? "";
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

    this.model.update(m => ({ ...m, attribute_mapping: map }));
  }
}
