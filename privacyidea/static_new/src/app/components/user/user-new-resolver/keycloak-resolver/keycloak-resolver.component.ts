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
    MatButtonToggle
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
      data.base_url = "http://localhost:8080";
    }
    if (!data.timeout) {
      data.timeout = 60;
    }
    if (data.verify_tls === undefined) {
      data.verify_tls = true;
    }

    if (!data.config_authorization || Object.keys(data.config_authorization).length === 0) {
      data.config_authorization = {
        method: "POST",
        endpoint: "/realms/{realm}/protocol/openid-connect/token",
        headers: "{\"Content-Type\": \"application/x-www-form-urlencoded\"}",
        requestMapping: "grant_type=password&client_id=admin-cli&username={username}&password={password}",
        responseMapping: "{\"Authorization\": \"Bearer {access_token}\"}"
      };
    }
    if (!data.config_user_auth || Object.keys(data.config_user_auth).length === 0) {
      data.config_user_auth = {
        method: "POST",
        endpoint: "/realms/{realm}/protocol/openid-connect/token",
        headers: "{\"Content-Type\": \"application/x-www-form-urlencoded\"}",
        requestMapping: "grant_type=password&client_id=admin-cli&username={username}&password={password}"
      };
    }
    if (!data.config_get_user_list || Object.keys(data.config_get_user_list).length === 0) {
      data.config_get_user_list = {
        method: "GET",
        endpoint: "/admin/realms/{realm}/users"
      };
    }
    if (!data.config_get_user_by_id || Object.keys(data.config_get_user_by_id).length === 0) {
      data.config_get_user_by_id = {
        method: "GET",
        endpoint: "/admin/realms/{realm}/users/{userid}"
      };
    }
    if (!data.config_get_user_by_name || Object.keys(data.config_get_user_by_name).length === 0) {
      data.config_get_user_by_name = {
        method: "GET",
        endpoint: "/admin/realms/{realm}/users",
        requestMapping: "{\"username\": \"{username}\", \"exact\": true}"
      };
    }
  }
}
