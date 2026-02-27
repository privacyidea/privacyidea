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
import { Component, effect, signal } from "@angular/core";
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
import { AttributeMappingRow, HttpResolverComponent } from "../http-resolver/http-resolver.component";
import { MatButtonToggle, MatButtonToggleGroup } from "@angular/material/button-toggle";
import { HttpConfigComponent } from "../http-resolver/http-config/http-config.component";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { HttpGroupsAttributeComponent } from "../http-resolver/http-groups-attribute/http-groups-attribute.component";

@Component({
  selector: "app-keycloak-resolver",
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
    ClearableInputComponent,
    HttpGroupsAttributeComponent
  ],
  templateUrl: "../http-resolver/http-resolver.component.html",
  styleUrl: "../http-resolver/http-resolver.component.scss"
})
export class KeycloakResolverComponent extends HttpResolverComponent {
  override isAdvanced: boolean = true;
  override isAuthorizationExpanded: boolean = true;
  override defaultMapping = signal<AttributeMappingRow[]>([
    { privacyideaAttr: "userid", userStoreAttr: "id" },
    { privacyideaAttr: "username", userStoreAttr: "userPrincipalName" },
    { privacyideaAttr: "email", userStoreAttr: "mail" },
    { privacyideaAttr: "givenname", userStoreAttr: "firstName" },
    { privacyideaAttr: "surname", userStoreAttr: "lastName" }
  ]);

  constructor() {
    super();
    effect(() => {
      this.initializeKeycloakData();
    });
  }

  protected initializeKeycloakData(): void {
    const data: any = this.data();
    if (!data) return;

    if (!data.base_url) {
      this.baseUrlControl.setValue("http://localhost:8080", { emitEvent: false });
    }
    if (!data.timeout) {
      this.timeoutControl.setValue(60, { emitEvent: false });
    }
    if (data.verify_tls === undefined) {
      this.verifyTlsControl.setValue(true, { emitEvent: false });
    }

    if (!data.config_authorization || Object.keys(data.config_authorization).length === 0) {
      this.configAuthorizationGroup.patchValue({
        method: "POST",
        endpoint: "/realms/{realm}/protocol/openid-connect/token",
        headers: "{\"Content-Type\": \"application/x-www-form-urlencoded\"}",
        requestMapping: "grant_type=password&client_id=admin-cli&username={username}&password={password}",
        responseMapping: "{\"Authorization\": \"Bearer {access_token}\"}"
      }, { emitEvent: false });
    }
    if (!data.config_user_auth || Object.keys(data.config_user_auth).length === 0) {
      this.configUserAuthGroup.patchValue({
        method: "POST",
        endpoint: "/realms/{realm}/protocol/openid-connect/token",
        headers: "{\"Content-Type\": \"application/x-www-form-urlencoded\"}",
        requestMapping: "grant_type=password&client_id=admin-cli&username={username}&password={password}"
      }, { emitEvent: false });
    }
    if (!data.config_get_user_list || Object.keys(data.config_get_user_list).length === 0) {
      this.configGetUserListGroup.patchValue({
        method: "GET",
        endpoint: "/admin/realms/{realm}/users"
      }, { emitEvent: false });
    }
    if (!data.config_get_user_by_id || Object.keys(data.config_get_user_by_id).length === 0) {
      this.configGetUserByIdGroup.patchValue({
        method: "GET",
        endpoint: "/admin/realms/{realm}/users/{userid}"
      }, { emitEvent: false });
    }
    if (!data.config_get_user_by_name || Object.keys(data.config_get_user_by_name).length === 0) {
      this.configGetUserByNameGroup.patchValue({
        method: "GET",
        endpoint: "/admin/realms/{realm}/users",
        requestMapping: "{\"username\": \"{username}\", \"exact\": true}"
      }, { emitEvent: false });
    }
  }
}
