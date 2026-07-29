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

import { HttpClient, HttpHeaders } from "@angular/common/http";
import { computed, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { MatDialog } from "@angular/material/dialog";
import { Router } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { AUTH_DATA_STORAGE_KEY, BEARER_TOKEN_STORAGE_KEY } from "@core/constants";
import { environment } from "@env/environment";
import { PolicyAction } from "@services/auth/policy-actions";
import { DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { LocalService, LocalServiceInterface } from "@services/local/local.service";
import { VersioningService, VersioningServiceInterface } from "@services/version/version.service";
import { tokenTypes } from "@utils/token.utils";
import { catchError, Observable, tap, throwError } from "rxjs";

export type AuthResponse = PiResponse<AuthData, AuthDetail>;

export enum LogLevel {
  NotSet = 0,
  Debug = 10,
  Info = 20,
  Warning = 30,
  Error = 40,
  Critical = 50
}

export interface ContainerWizardConfig {
  enabled: boolean;
  type: string;
  registration: boolean;
  template: string | null;
}

export interface AuthData {
  log_level: number;
  menus: string[];
  realm: string;
  rights: string[];
  role: AuthRole;
  token: string;
  username: string;
  logout_time: number;
  audit_page_size: number;
  token_page_size: number;
  user_page_size: number;
  policy_template_url: string;
  default_tokentype: string;
  default_container_type: string;
  user_details: boolean;
  token_wizard: boolean;
  token_wizard_2nd: boolean;
  admin_dashboard: boolean;
  dialog_no_token: boolean;
  search_on_enter: boolean;
  timeout_action: string;
  token_rollover?: Record<string, string[]>;
  hide_welcome: boolean;
  hide_buttons: boolean;
  deletion_confirmation: boolean;
  show_seed: boolean;
  show_node: string;
  subscription_status: number;
  subscription_status_push: number;
  qr_image_android: string | null;
  qr_image_ios: string | null;
  qr_image_custom: string | null;
  logout_redirect_url: string;
  require_description: string[];
  rss_age: number;
  container_wizard: ContainerWizardConfig;
}

export interface JwtData {
  username: string;
  realm: string;
  nonce: string;
  role: AuthRole;
  authtype: string;
  exp: number;
  rights: string[];
}

export type AuthRole = "admin" | "user" | "";

export interface WebAuthnSignRequestData {
  challenge: string;
  allowCredentials: {
    id: string;
    type?: PublicKeyCredentialType;
    transports?: AuthenticatorTransport[];
  }[];
  rpId: string;
  userVerification: UserVerificationRequirement;
  timeout?: number;
}

export interface MultiChallenge {
  client_mode: string;
  message: string;
  serial: string;
  transaction_id: string;
  type: string;
  attributes?: {
    webAuthnSignRequest?: WebAuthnSignRequestData;
  };
}

export interface AuthDetail {
  username?: string;
  attributes?: {
    hideResponseInput?: boolean;
  };
  client_mode?: string;
  loginmode?: string;
  message?: string;
  messages?: string[];
  multi_challenge?: MultiChallenge[];
  serial?: string;
  threadid?: number;
  transaction_id?: string;
  transaction_ids?: string[];
  type?: string;
}

export type TwoStepValue = "disabled" | "allow" | "force";

/**
 * Parameters for password-based authentication. Covers standard login, remote
 * login (password omitted), and challenge response (transaction_id set).
 */
export interface PasswordLoginParams {
  username: string;
  password?: string;
  realm?: string;
  transaction_id?: string;
}

/**
 * Parameters for WebAuthn second-factor authentication. Mirrors
 * `PasskeyCheckParams` plus `username` and a nullable `userHandle`.
 */
export interface WebAuthnLoginParams {
  transaction_id: string;
  username: string;
  credential_id: string;
  authenticatorData: string;
  clientDataJSON: string;
  signature: string;
  userHandle: string | null;
}

/**
 * Union of all parameter shapes accepted by `authenticate()`.
 * Imported `PasskeyCheckParams` from `validate.service` would create a
 * cycle, so callers pass the structurally compatible shape directly.
 */
export type AuthenticateParams =
  | PasswordLoginParams
  | WebAuthnLoginParams
  | {
  transaction_id: string;
  credential_id: string;
  authenticatorData: string;
  clientDataJSON: string;
  signature: string;
  userHandle: string;
};

export interface AuthServiceInterface {
  // Properties
  readonly authUrl: string;

  // Writable Signals
  readonly jwtData: WritableSignal<JwtData | null>;
  readonly authData: WritableSignal<AuthData | null>;
  readonly authenticationAccepted: WritableSignal<boolean>;

  // Signals
  readonly jwtNonce: Signal<string>;
  readonly authtype: Signal<"cookie" | "none">;
  readonly jwtExpDate: Signal<Date | null>;
  readonly jwtLogoutTimeS: Signal<number | null>;
  readonly logoutTimeS: Signal<number | null>;
  readonly isAuthenticated: Signal<boolean>;
  readonly logLevel: Signal<number>;
  readonly menus: Signal<string[]>;
  readonly realm: Signal<string>;
  readonly rights: Signal<string[]>;
  readonly rightsWithValues: Signal<Record<string, string | null>>;
  readonly role: Signal<AuthRole>;
  readonly token: Signal<string>;
  readonly username: Signal<string>;
  readonly auditPageSize: Signal<number>;
  readonly tokenPageSize: Signal<number | null>;
  readonly userPageSize: Signal<number>;
  readonly policyTemplateUrl: Signal<string>;
  readonly defaultTokentype: Signal<string>;
  readonly defaultContainerType: Signal<string>;
  readonly userDetails: Signal<boolean>;
  readonly tokenWizard: Signal<boolean>;
  readonly tokenWizard2nd: Signal<boolean>;
  readonly adminDashboard: Signal<boolean>;
  readonly dialogNoToken: Signal<boolean>;
  readonly searchOnEnter: Signal<boolean>;
  readonly timeoutAction: Signal<string>;
  readonly tokenRollover: Signal<string[]>;
  readonly hideWelcome: Signal<boolean>;
  readonly hideButtons: Signal<boolean>;
  readonly deletionConfirmation: Signal<boolean>;
  readonly showSeed: Signal<boolean>;
  readonly showNode: Signal<string>;
  readonly subscriptionStatus: Signal<number>;
  readonly subscriptionStatusPush: Signal<number>;
  readonly qrImageAndroid: Signal<string | null>;
  readonly qrImageIOS: Signal<string | null>;
  readonly qrImageCustom: Signal<string | null>;
  readonly logoutRedirectUrl: Signal<string>;
  readonly requireDescription: Signal<string[]>;
  readonly rssAge: Signal<number>;
  readonly containerWizard: Signal<{
    enabled: boolean;
    type: string | null;
    registration: boolean;
    template: string | null;
  }>;
  readonly isSelfServiceUser: Signal<boolean>;

  // Methods
  getHeaders(): HttpHeaders;

  authenticate(params: AuthenticateParams): Observable<AuthResponse>;

  acceptAuthentication(): void;

  logout(): void;

  actionAllowed(action: PolicyAction): boolean;

  actionsAllowed(actions: PolicyAction[]): boolean;

  oneActionAllowed(actions: PolicyAction[]): boolean;

  anyContainerActionAllowed(): boolean;

  tokenEnrollmentAllowed(): boolean;

  anyTokenActionAllowed(): boolean;

  checkForceServerGenerateOTPKey(tokenType: string): boolean;

  check2Step(tokenType: string): TwoStepValue;
}

@Injectable({
  providedIn: "root"
})
export class AuthService implements AuthServiceInterface {
  readonly authUrl = environment.proxyUrl + "/auth";
  // Writable Signals
  readonly jwtData = signal<JwtData | null>(null);
  readonly authData = signal<AuthData | null>(null);
  readonly authenticationAccepted = signal<boolean>(false);
  // Computed signals
  readonly jwtNonce = computed(() => this.jwtData()?.nonce || "");
  readonly authtype = computed(() => (this.jwtData()?.authtype || this.jwtData() ? "cookie" : "none"));
  readonly jwtExpDate = computed(() => {
    const exp = this.jwtData()?.exp;
    return exp ? new Date(exp * 1000) : null;
  });
  readonly jwtLogoutTimeS = computed(() => {
    const expiration = this.jwtExpDate();
    if (expiration == null) return null;
    const now = new Date();
    return Math.max(0, Math.floor((expiration.getTime() - now.getTime()) / 1000));
  });
  readonly logoutTimeS = computed(() => this.authData()?.logout_time || null);
  readonly isAuthenticated = computed(() => this.authenticationAccepted() && !!this.authData());
  readonly logLevel = computed(() => this.authData()?.log_level || LogLevel.NotSet);
  readonly menus = computed(() => this.authData()?.menus || []);
  readonly realm = computed(() => this.jwtData()?.realm || this.authData()?.realm || "");
  readonly rights = computed(() => this.jwtData()?.rights || this.authData()?.rights || []);
  readonly rightsWithValues = computed(() => {
    const rightsList = this.rights();
    const result: Record<string, string | null> = {};
    rightsList.forEach((entry) => {
      const equation_index = entry.indexOf("=");
      if (equation_index === -1) {
        if (!(entry in result)) {
          // avoid overwriting existing keys with null if they have a value in another entry
          result[entry] = null;
        }
      } else {
        const key = entry.substring(0, equation_index);
        result[key] = entry.substring(equation_index + 1);
      }
    });
    return result;
  });
  readonly role = computed(() => this.jwtData()?.role || this.authData()?.role || "");
  readonly token = computed(() => this.authData()?.token || "");
  readonly username = computed(() => this.jwtData()?.username || this.authData()?.username || "");
  readonly auditPageSize = computed(() => this.authData()?.audit_page_size || 10);
  readonly tokenPageSize = computed(() => this.authData()?.token_page_size || null);
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
  readonly timeoutAction = computed(() => this.authData()?.timeout_action || "logout");
  readonly tokenRollover = computed(() => Object.keys(this.authData()?.token_rollover || {}));
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
        type: null,
        registration: false,
        template: null
      }
  );
  readonly isSelfServiceUser = computed(() => this.role() === "user");

  constructor() {
    this.restoreSession();
  }

  getHeaders(): HttpHeaders {
    return new HttpHeaders({
      "PI-Authorization": this.localService.getData(BEARER_TOKEN_STORAGE_KEY) || ""
    });
  }

  authenticate(params: AuthenticateParams): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(this.authUrl, JSON.stringify(params), {
        headers: new HttpHeaders({
          "Content-Type": "application/json",
          Accept: "application/json"
        }),
        withCredentials: true
      })
      .pipe(
        tap((response) => {
          const value = response.result?.value;
          if (response?.result?.status && value) {
            this.acceptAuthentication();
            this.authData.set(value);
            this.jwtData.set(this.decodeJwtPayload(value.token));
            this.localService.saveData(BEARER_TOKEN_STORAGE_KEY, value.token);
            this.localService.saveData(AUTH_DATA_STORAGE_KEY, JSON.stringify(this.persistableAuthData(value)));
            // Update version after login — the hide_version policy strips the
            // version from pre-login responses, but the /auth response includes
            // it because g.logged_in_user is set during authentication.
            if (response.versionnumber) {
              this.versioningService.rawVersion.set(response.versionnumber);
            }
          }
        }),
        catchError((error) => {
          return throwError(() => error);
        })
      );
  }

  acceptAuthentication(): void {
    this.authenticationAccepted.set(true);
  }

  logout(): void {
    this.dialog.closeAll();
    this.authData.set(null);
    this.jwtData.set(null);
    this.clearStoredSession();
    this.authenticationAccepted.set(false);
    this.dashboardDataStore.invalidate();
    this.router.navigate(["login"]);
  }

  actionAllowed(action: PolicyAction): boolean {
    return this.rights().includes(action);
  }

  actionsAllowed(actions: PolicyAction[]): boolean {
    return actions.every((action) => this.actionAllowed(action));
  }

  oneActionAllowed(actions: PolicyAction[]): boolean {
    return actions.some((action) => this.actionAllowed(action));
  }

  anyContainerActionAllowed(): boolean {
    return this.oneActionAllowed([
      "container_list",
      "container_create",
      "container_template_list",
      "container_template_create"
    ]);
  }

  tokenEnrollmentAllowed(): boolean {
    const enrollPolicies = tokenTypes.map((type) => ("enroll" + type.key.toUpperCase()) as PolicyAction);
    return this.oneActionAllowed(enrollPolicies);
  }

  anyTokenActionAllowed(): boolean {
    const allowed = this.oneActionAllowed(["tokenlist", "getchallenges", "getserial", "machinelist"]);
    return allowed || this.tokenEnrollmentAllowed();
  }

  checkForceServerGenerateOTPKey(tokenType: string): boolean {
    return this.actionAllowed((tokenType + "_force_server_generate") as PolicyAction);
  }

  check2Step(tokenType: string): TwoStepValue {
    const key = tokenType + "_2step";
    const value = this.rightsWithValues()[key];
    if (value === "allow") {
      return "allow";
    } else if (value === "force") {
      return "force";
    } else {
      return "disabled";
    }
  }

  private readonly router = inject(Router);
  private readonly dialog = inject(MatDialog);
  private readonly localService: LocalServiceInterface = inject(LocalService);
  private readonly http = inject(HttpClient);
  private readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  private readonly dashboardDataStore = inject(DashboardDataStore);
  decodeJwtPayload(token: string): JwtData | null {
    try {
      const parts = token.split(".");
      if (parts.length !== 3) {
        throw new Error("Invalid JWT token format");
      }

      const payloadBase64 = parts[1];
      const payloadJson = atob(payloadBase64.replace(/-/g, "+").replace(/_/g, "/"));
      return JSON.parse(payloadJson);
    } catch (e) {
      console.error("Failed to decode JWT:", e);
      return null;
    }
  }

  /**
   * Strip the fields that the bearer token already carries before persisting the auth data.
   * The token (stored separately) is the source of truth for identity and rights via the
   * decoded JWT, so the token string and the JWT claims (rights, role, username, realm) are
   * not duplicated into storage; everything that remains is UI/policy config not in the JWT.
   */
  private persistableAuthData(authData: AuthData): Omit<AuthData, "token" | "rights" | "role" | "username" | "realm"> {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { token, rights, role, username, realm, ...rest } = authData;
    return rest;
  }

  /**
   * Rehydrate the session from storage on bootstrap so a full page reload (e.g. switching
   * the UI language, which loads a different locale bundle) does not drop an active login.
   * The token and the auth data are restored only while the JWT is still valid; an
   * expired or corrupt session is cleared instead.
   */
  private restoreSession(): void {
    const token = this.localService.getData(BEARER_TOKEN_STORAGE_KEY);
    if (!token) {
      return;
    }
    const jwt = this.decodeJwtPayload(token);
    // Treat a missing/zero exp as expired: such a token cannot establish a valid session.
    if (!jwt || !jwt.exp || jwt.exp * 1000 <= Date.now()) {
      this.clearStoredSession();
      return;
    }
    const storedAuthData = this.localService.getData(AUTH_DATA_STORAGE_KEY);
    if (!storedAuthData) {
      // A token without its auth data cannot be restored; clear it so getHeaders() does not
      // keep sending a bearer token for a session the UI considers logged out.
      this.clearStoredSession();
      return;
    }
    try {
      this.authData.set(JSON.parse(storedAuthData) as AuthData);
      this.jwtData.set(jwt);
      this.authenticationAccepted.set(true);
    } catch {
      this.clearStoredSession();
    }
  }

  private clearStoredSession(): void {
    this.localService.removeData(BEARER_TOKEN_STORAGE_KEY);
    this.localService.removeData(AUTH_DATA_STORAGE_KEY);
  }
}
