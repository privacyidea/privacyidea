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
import { Component, effect, inject, ResourceStatus } from "@angular/core";
import { FormControl, FormsModule } from "@angular/forms";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatOption } from "@angular/material/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatCardModule } from "@angular/material/card";
import { HttpErrorResponse } from "@angular/common/http";
import { PiResponse } from "../../../app.component";

import { ResolverService, ResolverType } from "../../../services/resolver/resolver.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { PasswdResolverComponent } from "./passwd-resolver/passwd-resolver.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { LdapResolverComponent } from "./ldap-resolver/ldap-resolver.component";
import { SqlResolverComponent } from "./sql-resolver/sql-resolver.component";
import { ScimResolverComponent } from "./scim-resolver/scim-resolver.component";
import { HttpResolverComponent } from "./http-resolver/http-resolver.component";
import { EntraidResolverComponent } from "./entraid-resolver/entraid-resolver.component";
import { KeycloakResolverComponent } from "./keycloak-resolver/keycloak-resolver.component";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "../../../route_paths";

@Component({
  selector: "app-user-new-resolver",
  standalone: true,
  imports: [
    FormsModule,
    MatFormField,
    MatLabel,
    MatError,
    MatInput,
    MatSelectModule,
    MatSelect,
    MatOption,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    PasswdResolverComponent,
    ScrollToTopDirective,
    LdapResolverComponent,
    SqlResolverComponent,
    ScimResolverComponent,
    HttpResolverComponent,
    EntraidResolverComponent,
    KeycloakResolverComponent
  ],
  templateUrl: "./user-new-resolver.component.html",
  styleUrl: "./user-new-resolver.component.scss"
})
export class UserNewResolverComponent {
  private readonly resolverService = inject(ResolverService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);
  readonly sqlPresets = [
    {
      name: "Wordpress",
      table: "wp_users",
      map: "{ \"userid\" : \"ID\", \"username\": \"user_login\", \"email\" : \"user_email\", \"givenname\" : \"display_name\", \"password\" : \"user_pass\" }"
    },
    {
      name: "OTRS",
      table: "users",
      map: "{ \"userid\" : \"id\", \"username\": \"login\", \"givenname\" : \"first_name\", \"surname\" : \"last_name\", \"password\" : \"pw\" }"
    },
    {
      name: "TINE 2.0",
      table: "tine20_accounts",
      map: "{ \"userid\" : \"id\", \"username\": \"login_name\", \"email\" : \"email\", \"givenname\" : \"first_name\", \"surname\" : \"last_name\", \"password\" : \"password\" }"
    },
    {
      name: "Owncloud",
      table: "oc_users",
      map: "{ \"userid\" : \"uid\", \"username\": \"uid\", \"givenname\" : \"displayname\", \"password\" : \"password\" }"
    },
    {
      name: "Typo3",
      table: "be_users",
      map: "{ \"userid\" : \"uid\", \"username\": \"username\", \"givenname\" : \"realName\", \"password\" : \"password\", \"email\": \"email\" }"
    },
    {
      name: "Drupal",
      table: "user",
      map: "{\"userid\": \"uid\", \"username\": \"name\", \"email\": \"mail\", \"password\": \"pass\" }"
    }
  ];
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
  private editInitialized = false;
  additionalFormFields: { [key: string]: FormControl<any> } = {};
  resolverName = "";
  resolverType: ResolverType = "passwdresolver";
  formData: Record<string, any> = {
    fileName: "/etc/passwd"
  };
  isSaving = false;
  isTesting = false;
  testUsername = "";
  testUserId = "";

  constructor() {
    effect(() => {
      const selectedName = this.resolverService.selectedResolverName();

      if (!selectedName) {
        if (this.editInitialized) {
          this.resolverName = "";
          this.resolverType = "passwdresolver";
          this.formData = {
            fileName: "/etc/passwd"
          };
          this.editInitialized = false;
        }
        return;
      }

      const resourceRef = this.resolverService.selectedResolverResource;

      if (resourceRef.status() === ResourceStatus.Loading || resourceRef.status() === ResourceStatus.Reloading) {
        this.editInitialized = false;
        return;
      }

      const resource = resourceRef.value();

      if (!resource?.result?.value) {
        return;
      }

      if (this.editInitialized) {
        return;
      }

      const resolverData = resource.result.value;
      const resolver = resolverData[selectedName];

      if (resolver) {
        this.resolverName = resolver.resolvername || selectedName;
        this.resolverType = resolver.type;
        this.formData = { ...(resolver.data || {}) };
        this.editInitialized = true;
      }
    });
  }

  get isEditMode(): boolean {
    return !!this.resolverService.selectedResolverName();
  }

  get isAdditionalFieldsValid(): boolean {
    return Object.values(this.additionalFormFields).every(control => control.valid);
  }

  onTypeChange(type: ResolverType): void {
    if (!this.isEditMode) {
      this.formData = {};
      this.additionalFormFields = {};

      if (type === "passwdresolver") {
        this.formData = {
          fileName: "/etc/passwd"
        };
      } else if (type === "ldapresolver") {
        this.formData = {
          TLS_VERSION: "TLSv1_3",
          TLS_VERIFY: true,
          SCOPE: "SUBTREE",
          AUTHTYPE: "simple",
          TIMEOUT: 5,
          CACHE_TIMEOUT: 120,
          SIZELIMIT: 500,
          SERVERPOOL_ROUNDS: 2,
          SERVERPOOL_SKIP: 30,
          UIDTYPE: "DN"
        };
      } else if (type === "sqlresolver") {
        this.formData = {
          Driver: "mysql+pymysql",
          Server: "localhost",
          Limit: 500,
          poolSize: 5,
          poolTimeout: 10,
          poolRecycle: 7200
        };
      } else if (type === "entraidresolver") {
        this.formData = {
          base_url: "https://graph.microsoft.com/v1.0",
          authority: "https://login.microsoftonline.com/{tenant}",
          client_credential_type: "secret",
          client_certificate: {},
          timeout: 60,
          verify_tls: true,
          config_get_user_by_id: { "method": "GET", "endpoint": "/users/{userid}" },
          config_get_user_by_name: { "method": "GET", "endpoint": "/users/{username}" },
          config_get_user_list: {
            "method": "GET",
            "endpoint": "/users",
            "headers": "{\"ConsistencyLevel\": \"eventual\"}"
          },
          config_create_user: {
            "method": "POST", "endpoint": "/users",
            "requestMapping": "{\"accountEnabled\": true, \"displayName\": \"{givenname} {surname}\", \"mailNickname\": \"{givenname}\", \"passwordProfile\": {\"password\": \"{password}\"}}"
          },
          config_edit_user: { "method": "PATCH", "endpoint": "/users/{userid}" },
          config_delete_user: { "method": "DELETE", "endpoint": "/users/{userid}" },
          config_user_auth: {
            "method": "POST",
            "headers": "{\"Content-Type\": \"application/x-www-form-urlencoded\"}",
            "endpoint": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            "requestMapping": "client_id={client_id}&scope=https://graph.microsoft.com/.default&username={username}&password={password}&grant_type=password&client_secret={client_credential}"
          }
        };
      } else if (type === "keycloakresolver") {
        this.formData = {
          config_authorization: {
            method: "POST",
            endpoint: "/realms/{realm}/protocol/openid-connect/token",
            headers: "{\"Content-Type\": \"application/x-www-form-urlencoded\"}",
            requestMapping: "grant_type=password&client_id=admin-cli&username={username}&password={password}",
            responseMapping: "{\"Authorization\": \"Bearer {access_token}\"}"
          },
          config_user_auth: {
            method: "POST",
            endpoint: "/realms/{realm}/protocol/openid-connect/token",
            headers: "{\"Content-Type\": \"application/x-www-form-urlencoded\"}",
            requestMapping: "grant_type=password&client_id=admin-cli&username={username}&password={password}"
          },
          config_get_user_list: {
            method: "GET",
            endpoint: "/admin/realms/{realm}/users"
          },
          config_get_user_by_id: {
            method: "GET",
            endpoint: "/admin/realms/{realm}/users/{userid}"
          },
          config_get_user_by_name: {
            method: "GET",
            endpoint: "/admin/realms/{realm}/users",
            requestMapping: "{\"username\": \"{username}\", \"exact\": true}"
          }
        };
      } else if (type === "scimresolver") {
        this.formData = {
          Authserver: "http://localhost:8080/osiam-auth-server",
          Resourceserver: "http://localhost:8080/osiam-resource-server",
          Mapping: "{\"userName\": \"username\", \"id\": \"userid\", \"emails.0.value\": \"email\"}"
        };
      } else if (type === "httpresolver") {
        this.formData = {
          method: "GET",
          endpoint: "https://example.com/path/to/users/:userid",
          requestMapping: "{}",
          headers: '{"Content-Type":"application/json; charset=UTF-8"}',
          responseMapping: '{"username":"{username}", "userid":"{userid}"}',
          hasSpecialErrorHandler: false,
          errorResponse: '{"success": false, "message": "An error occurred!"}'
        };
      }
    }
  }

  applySqlPreset(preset: any): void {
    this.formData = {
      ...this.formData,
      Table: preset.table,
      Map: preset.map,
      poolSize: 5,
      poolTimeout: 10,
      poolRecycle: 7200,
      Editable: true
    };
  }

  applyLdapPreset(preset: any): void {
    this.formData = {
      ...this.formData,
      LOGINNAMEATTRIBUTE: preset.loginName,
      LDAPSEARCHFILTER: preset.searchFilter,
      USERINFO: preset.userInfo,
      UIDTYPE: preset.uidType,
      MULTIVALUEATTRIBUTES: ""
    };
  }


  onSave(): void {
    const name = this.resolverName.trim();
    if (!name) {
      this.notificationService.openSnackBar($localize`Please enter a resolver name.`);
      return;
    }
    if (!this.resolverType) {
      this.notificationService.openSnackBar($localize`Please select a resolver type.`);
      return;
    }

    if (!this.isAdditionalFieldsValid) {
      this.notificationService.openSnackBar($localize`Please fill in all required fields.`);
      return;
    }

    const payload: any = {
      type: this.resolverType,
      ...this.formData
    };

    for (const [key, control] of Object.entries(this.additionalFormFields)) {
      if (!control) continue;
      payload[key] = control.value;
    }

    this.isSaving = true;

    this.resolverService
      .postResolver(name, payload)
      .subscribe({
        next: (res: PiResponse<any, any>) => {
          if (res.result?.status === true && (res.result.value ?? 0) >= 0) {
            this.notificationService.openSnackBar(
              this.isEditMode
                ? $localize`Resolver "${name}" updated.`
                : $localize`Resolver "${name}" created.`
            );
            this.resolverService.resolversResource.reload?.();

            if (!this.isEditMode) {
              this.resolverName = "";
              this.formData = {};
              this.additionalFormFields = {};
              this.router.navigateByUrl(ROUTE_PATHS.USERS_SOURCES);
            }
          } else {
            const message = res.detail?.description || res.result?.error?.message || $localize`Unknown error occurred.`;
            this.notificationService.openSnackBar(
              $localize`Failed to save resolver. ${message}`
            );
          }
        },
        error: (err: HttpErrorResponse) => {
          const message = err.error?.result?.error?.message || err.message;
          this.notificationService.openSnackBar(
            $localize`Failed to save resolver. ${message}`
          );
        }
      })
      .add(() => (this.isSaving = false));
  }

  onTest(): void {
    this.executeTest();
  }

  onQuickTest() {
    this.executeTest(true);
  }

  private executeTest(quickTest = false): void {
    if (!this.resolverType) {
      this.notificationService.openSnackBar($localize`Please select a resolver type.`);
      return;
    }

    if (!this.isAdditionalFieldsValid) {
      this.notificationService.openSnackBar($localize`Please fill in all required fields.`);
      return;
    }

    this.isTesting = true;

    const payload: any = {
      type: this.resolverType,
      ...this.formData,
      test_username: this.testUsername,
      test_userid: this.testUserId
    };

    if (quickTest) {
      payload["SIZELIMIT"] = 1;
    }

    if (this.isEditMode) {
      payload["resolver"] = this.resolverName;
    }

    for (const [key, control] of Object.entries(this.additionalFormFields)) {
      if (!control) continue;
      payload[key] = control.value;
    }

    this.resolverService
      .postResolverTest(payload)
      .subscribe({
        next: (res: PiResponse<any, any>) => {
          if (res.result?.status === true && (res.result.value ?? 0) >= 0) {
            this.notificationService.openSnackBar(
              $localize`Resolver test executed. Check server response.`
            );
          } else {
            const message = res.detail?.description || res.result?.error?.message || $localize`Unknown error occurred.`;
            this.notificationService.openSnackBar(
              $localize`Failed to test resolver. ${message}`
            );
          }
        },
        error: (err: HttpErrorResponse) => {
          const message = err.error?.result?.error?.message || err.message;
          this.notificationService.openSnackBar(
            $localize`Failed to test resolver. ${message}`
          );
        }
      })
      .add(() => (this.isTesting = false));
  }

  updateAdditionalFormFields(event: { [key: string]: FormControl<any> | undefined | null }): void {
    const validControls: { [key: string]: FormControl<any> } = {};
    for (const key in event) {
      if (event.hasOwnProperty(key) && event[key] instanceof FormControl) {
        validControls[key] = event[key] as FormControl<any>;
      }
    }
    this.additionalFormFields = validControls;
  }
}
