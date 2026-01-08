import { Component, signal } from "@angular/core";
import { AttributeMappingRow, HttpResolverComponent } from "../http-resolver/http-resolver.component";
import { FormsModule } from "@angular/forms";
import { MatFormField, MatHint, MatInput, MatLabel } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatSlideToggle } from "@angular/material/slide-toggle";
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
    MatSlideToggle,
    MatHint,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatDivider
  ],
  templateUrl: "../http-resolver/http-resolver.component.html",
  styleUrl: "../http-resolver/http-resolver.component.scss"
})
export class EntraidResolverComponent extends HttpResolverComponent {
  override isAdvanced: boolean = true;

  override ngOnInit(): void {
    const data: any = this.data();

    if (!data.base_url) {
      data.base_url = "https://graph.microsoft.com/v1.0";
    }
    if (!data.authority) {
      data.authority = "https://login.microsoftonline.com/{tenant}";
    }
    if (!data.client_credential_type) {
      data.client_credential_type = "secret";
    }
    if (!data.client_certificate) {
      data.client_certificate = {};
    }
    if (!data.timeout) {
      data.timeout = 60;
    }
    if (!data.verify_tls && data.verify_tls !== false) {
      data.verify_tls = true;
    }

    if (!data.config_get_user_by_id || Object.keys(data.config_get_user_by_id).length === 0) {
      data.config_get_user_by_id = { "method": "GET", "endpoint": "/users/{userid}" };
    }
    if (!data.config_get_user_by_name || Object.keys(data.config_get_user_by_name).length === 0) {
      data.config_get_user_by_name = { "method": "GET", "endpoint": "/users/{username}" };
    }
    if (!data.config_get_user_list || Object.keys(data.config_get_user_list).length === 0) {
      data.config_get_user_list = { "method": "GET", "endpoint": "/users", "headers": "{\"ConsistencyLevel\": \"eventual\"}" };
    }
    if (!data.config_create_user || Object.keys(data.config_create_user).length === 0) {
      data.config_create_user = {
        "method": "POST", "endpoint": "/users",
        "requestMapping": "{\"accountEnabled\": true, \"displayName\": \"{givenname} {surname}\", \"mailNickname\": \"{givenname}\", \"passwordProfile\": {\"password\": \"{password}\"}}"
      };
    }
    if (!data.config_edit_user || Object.keys(data.config_edit_user).length === 0) {
      data.config_edit_user = { "method": "PATCH", "endpoint": "/users/{userid}" };
    }
    if (!data.config_delete_user || Object.keys(data.config_delete_user).length === 0) {
      data.config_delete_user = { "method": "DELETE", "endpoint": "/users/{userid}" };
    }
    if (!data.config_user_auth || Object.keys(data.config_user_auth).length === 0) {
      data.config_user_auth = {
        "method": "POST",
        "headers": "{\"Content-Type\": \"application/x-www-form-urlencoded\"}",
        "endpoint": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        "requestMapping": "client_id={client_id}&scope=https://graph.microsoft.com/.default&username={username}&password={password}&grant_type=password&client_secret={client_credential}"
      };
    }

    super.ngOnInit();
  }

  override defaultMapping = signal<AttributeMappingRow[]>([
    { privacyideaAttr: "userid", userStoreAttr: "id" },
    { privacyideaAttr: "username", userStoreAttr: "userPrincipalName" },
    { privacyideaAttr: "email", userStoreAttr: "mail" },
    { privacyideaAttr: "givenname", userStoreAttr: "givenName" },
    { privacyideaAttr: "mobile", userStoreAttr: "mobilePhone" },
    { privacyideaAttr: "phone", userStoreAttr: "businessPhones" },
    { privacyideaAttr: "surname", userStoreAttr: "surname" }
  ]);
}
