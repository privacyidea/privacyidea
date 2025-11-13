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

import { computed, signal } from "@angular/core";
import { AuthData, AuthDetail, AuthRole, AuthServiceInterface, JwtData } from "../../app/services/auth/auth.service";
import { MockAuthData, MockAuthDetail, MockPiResponse } from "../mock-services";
import { of } from "rxjs";
import { HttpHeaders } from "@angular/common/http";

export class MockAuthService implements AuthServiceInterface {
  // Properties
  readonly authUrl = "/auth";

  // Writable Signals
  readonly jwtData = signal<JwtData | null>(null);
  readonly authData = signal<AuthData | null>(MockAuthService.MOCK_AUTH_DATA);
  readonly authenticationAccepted = signal(false);

  // Signals
  readonly jwtNonce = signal(this.jwtData()?.nonce || "");
  readonly authtype = signal<"cookie" | "none">("cookie");
  readonly jwtExpDate = signal(new Date());
  readonly isAuthenticated = signal(true);
  readonly logLevel = signal(0);
  readonly menus = computed(() => this.authData()?.menus || []);
  readonly realm = computed(() => this.authData()?.realm || "");
  readonly rights = computed(() => this.authData()?.rights || []);
  readonly role = computed<AuthRole>(() => this.authData()?.role || "admin");
  readonly token = computed(() => this.authData()?.token || "");
  readonly username = computed(() => this.authData()?.username || "");
  readonly logoutTimeSeconds = computed(() => this.authData()?.logout_time || null);
  readonly auditPageSize = computed(() => this.authData()?.audit_page_size || 10);
  readonly tokenPageSize = computed(() => this.authData()?.token_page_size || 10);
  readonly userPageSize = computed(() => this.authData()?.user_page_size || 10);
  readonly policyTemplateUrl = computed(() => this.authData()?.policy_template_url || "");
  readonly defaultTokentype = computed(() => this.authData()?.default_tokentype || "hotp");
  readonly defaultContainerType = computed(() => this.authData()?.default_container_type || "generic");
  readonly userDetails = computed(() => this.authData()?.user_details || false);
  readonly tokenWizard = computed(() => this.authData()?.token_wizard || false);
  readonly tokenWizard2nd = computed(() => this.authData()?.token_wizard_2nd || false);
  readonly adminDashboard = computed(() => this.authData()?.admin_dashboard || false);
  readonly dialogNoToken = computed(() => this.authData()?.dialog_no_token || false);
  readonly searchOnEnter = computed(() => this.authData()?.search_on_enter || false);
  readonly timeoutAction = computed(() => this.authData()?.timeout_action || "");
  readonly tokenRollover = computed(() => this.authData()?.token_rollover || null);
  readonly hideWelcome = computed(() => this.authData()?.hide_welcome || false);
  readonly hideButtons = computed(() => this.authData()?.hide_buttons || false);
  readonly deletionConfirmation = computed(() => this.authData()?.deletion_confirmation || false);
  readonly showSeed = computed(() => this.authData()?.show_seed || false);
  readonly showNode = computed(() => this.authData()?.show_node || "");
  readonly subscriptionStatus = computed(() => this.authData()?.subscription_status || 0);
  readonly subscriptionStatusPush = computed(() => this.authData()?.subscription_status_push || 0);
  readonly qrImageAndroid = computed(() => this.authData()?.qr_image_android || null);
  readonly qrImageIOS = computed(() => this.authData()?.qr_image_ios || null);
  readonly qrImageCustom = computed(() => this.authData()?.qr_image_custom || null);
  readonly logoutRedirectUrl = computed(() => this.authData()?.logout_redirect_url || "");
  readonly requireDescription = computed(() => this.authData()?.require_description || []);
  readonly rssAge = computed(() => this.authData()?.rss_age || 0);
  readonly containerWizard = computed(
    () =>
      this.authData()?.container_wizard || {
        enabled: false,
        type: "",
        registration: false,
        template: null
      }
  );
  readonly isSelfServiceUser = computed(() => this.role() === "user");

  // Methods
  getHeaders = jest.fn().mockReturnValue(new HttpHeaders());
  authenticate = jest
    .fn()
    .mockReturnValue(of(MockPiResponse.fromValue<AuthData, AuthDetail>(new MockAuthData(), new MockAuthDetail())));
  acceptAuthentication = jest.fn();
  logout = jest.fn();
  actionAllowed = jest.fn().mockReturnValue(true);
  actionsAllowed = jest.fn().mockReturnValue(true);
  oneActionAllowed = jest.fn().mockReturnValue(true);
  anyContainerActionAllowed = jest.fn().mockReturnValue(true);
  tokenEnrollmentAllowed = jest.fn().mockReturnValue(true);
  anyTokenActionAllowed = jest.fn().mockReturnValue(true);
  checkForceServerGenerateOTPKey = jest.fn().mockReturnValue(false);

  static MOCK_AUTH_DATA: AuthData = {
    log_level: 0,
    menus: ["token_overview", "token_self-service_menu", "container_overview"],
    realm: "default",
    rights: [],
    role: "admin",
    token: "",
    username: "alice",
    logout_time: 3600,
    audit_page_size: 25,
    token_page_size: 10,
    user_page_size: 10,
    policy_template_url: "",
    default_tokentype: "",
    default_container_type: "",
    user_details: false,
    token_wizard: false,
    token_wizard_2nd: false,
    admin_dashboard: false,
    dialog_no_token: false,
    search_on_enter: false,
    timeout_action: "",
    token_rollover: null,
    hide_welcome: false,
    hide_buttons: false,
    deletion_confirmation: false,
    show_seed: false,
    show_node: "",
    subscription_status: 0,
    subscription_status_push: 0,
    qr_image_android: null,
    qr_image_ios: null,
    qr_image_custom: null,
    logout_redirect_url: "",
    require_description: [],
    rss_age: 0,
    container_wizard: {
      enabled: false,
      type: "",
      registration: false,
      template: null
    }
  };
}
