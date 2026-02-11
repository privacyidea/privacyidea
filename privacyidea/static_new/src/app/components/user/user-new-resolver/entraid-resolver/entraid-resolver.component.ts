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

import { Component, effect, signal } from "@angular/core";
import { AttributeMappingRow, HttpResolverComponent } from "../http-resolver/http-resolver.component";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatFormField, MatHint, MatInput, MatLabel } from "@angular/material/input";
import { MatError, MatOption, MatSelect } from "@angular/material/select";
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
import { MatButtonToggle, MatButtonToggleGroup } from "@angular/material/button-toggle";
import { HttpConfigComponent } from "../http-resolver/http-config/http-config.component";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";

@Component({
  selector: "app-entraid-resolver",
  standalone: true,
  imports: [
    FormsModule,
    MatFormField,
    MatLabel,
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
    MatError,
    ReactiveFormsModule,
    MatDivider,
    MatButtonToggleGroup,
    MatButtonToggle,
    HttpConfigComponent,
    ClearableInputComponent
  ],
  templateUrl: "../http-resolver/http-resolver.component.html",
  styleUrl: "../http-resolver/http-resolver.component.scss"
})
export class EntraidResolverComponent extends HttpResolverComponent {
  override isAdvanced: boolean = true;
  override isAuthorizationExpanded: boolean = true;
  override defaultMapping = signal<AttributeMappingRow[]>([
    { privacyideaAttr: "userid", userStoreAttr: "id" },
    { privacyideaAttr: "username", userStoreAttr: "userPrincipalName" },
    { privacyideaAttr: "email", userStoreAttr: "mail" },
    { privacyideaAttr: "givenname", userStoreAttr: "givenName" },
    { privacyideaAttr: "mobile", userStoreAttr: "mobilePhone" },
    { privacyideaAttr: "phone", userStoreAttr: "businessPhones" },
    { privacyideaAttr: "surname", userStoreAttr: "surname" }
  ]);

  constructor() {
    super();
    effect(() => {
      this.initializeEntraidData();
    });
  }

  protected initializeEntraidData(): void {
    const data: any = this.data();
    if (!data) return;

    if (!data.base_url) {
      this.baseUrlControl.setValue("https://graph.microsoft.com/v1.0", { emitEvent: false });
    }
    if (!data.authority) {
      this.authorityControl.setValue("https://login.microsoftonline.com/{tenant}", { emitEvent: false });
    }
    if (!data.client_credential_type) {
      this.clientCredentialTypeControl.setValue("secret", { emitEvent: false });
    }
    if (!data.timeout) {
      this.timeoutControl.setValue(60, { emitEvent: false });
    }
    if (data.verify_tls === undefined) {
      this.verifyTlsControl.setValue(true, { emitEvent: false });
    }

    if (!data.config_get_user_by_id || Object.keys(data.config_get_user_by_id).length === 0) {
      this.configGetUserByIdGroup.patchValue({ "method": "GET", "endpoint": "/users/{userid}" }, { emitEvent: false });
    }
    if (!data.config_get_user_by_name || Object.keys(data.config_get_user_by_name).length === 0) {
      this.configGetUserByNameGroup.patchValue({
        "method": "GET",
        "endpoint": "/users/{username}"
      }, { emitEvent: false });
    }
    if (!data.config_get_user_list || Object.keys(data.config_get_user_list).length === 0) {
      this.configGetUserListGroup.patchValue({
        "method": "GET",
        "endpoint": "/users",
        "headers": "{\"ConsistencyLevel\": \"eventual\"}"
      }, { emitEvent: false });
    }
    if (!data.config_create_user || Object.keys(data.config_create_user).length === 0) {
      this.configCreateUserGroup.patchValue({
        "method": "POST", "endpoint": "/users",
        "requestMapping": "{\"accountEnabled\": true, \"displayName\": \"{givenname} {surname}\", \"mailNickname\": \"{givenname}\", \"passwordProfile\": {\"password\": \"{password}\"}}"
      }, { emitEvent: false });
    }
    if (!data.config_edit_user || Object.keys(data.config_edit_user).length === 0) {
      this.configEditUserGroup.patchValue({ "method": "PATCH", "endpoint": "/users/{userid}" }, { emitEvent: false });
    }
    if (!data.config_delete_user || Object.keys(data.config_delete_user).length === 0) {
      this.configDeleteUserGroup.patchValue({
        "method": "DELETE",
        "endpoint": "/users/{userid}"
      }, { emitEvent: false });
    }
    if (!data.config_user_auth || Object.keys(data.config_user_auth).length === 0) {
      this.configUserAuthGroup.patchValue({
        "method": "POST",
        "headers": "{\"Content-Type\": \"application/x-www-form-urlencoded\"}",
        "endpoint": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        "requestMapping": "client_id={client_id}&scope=https://graph.microsoft.com/.default&username={username}&password={password}&grant_type=password&client_secret={client_credential}"
      }, { emitEvent: false });
    }
  }
}
