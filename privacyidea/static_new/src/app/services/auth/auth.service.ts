import { HttpClient, HttpHeaders } from "@angular/common/http";
import { computed, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { Observable, throwError } from "rxjs";
import { catchError, tap } from "rxjs/operators";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { BEARER_TOKEN_STORAGE_KEY } from "../../core/constants";
import { LocalService, LocalServiceInterface } from "../local/local.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { VersioningService, VersioningServiceInterface } from "../version/version.service";

export type AuthResponse = PiResponse<AuthData, AuthDetail>;

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
  token_rollover: any;
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
  container_wizard: {
    enabled: boolean;
  };
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

export interface MultiChallenge {
  client_mode: string;
  message: string;
  serial: string;
  transaction_id: string;
  type: string;
  attributes?: {
    webAuthnSignRequest?: any;
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

export interface AuthServiceInterface {
  authUrl: string;
  jwtData: WritableSignal<JwtData | null>;
  jwtNonce: Signal<string>;
  authtype: Signal<"cookie" | "none">;
  jwtExpDate: Signal<Date | null>;

  authData: () => AuthData | null;
  authenticationAccepted: () => boolean;

  isAuthenticated: () => boolean;

  getHeaders: () => HttpHeaders;

  logLevel: () => number;
  menus: () => string[];
  realm: () => string;
  rights: () => string[];
  role: () => AuthRole;
  token: () => string;
  username: () => string;
  logoutTimeSeconds: () => number | null;
  auditPageSize: () => number;
  tokenPageSize: () => number;
  userPageSize: () => number;
  policyTemplateUrl: () => string;
  defaultTokentype: () => string;
  defaultContainerType: () => string;
  userDetails: () => boolean;
  tokenWizard: () => boolean;
  tokenWizard2nd: () => boolean;
  adminDashboard: () => boolean;
  dialogNoToken: () => boolean;
  searchOnEnter: () => boolean;
  timeoutAction: () => string;
  tokenRollover: () => any;
  hideWelcome: () => boolean;
  hideButtons: () => boolean;
  deletionConfirmation: () => boolean;
  showSeed: () => boolean;
  showNode: () => string;
  subscriptionStatus: () => number;
  subscriptionStatusPush: () => number;
  qrImageAndroid: () => string | null;
  qrImageIOS: () => string | null;
  qrImageCustom: () => string | null;
  logoutRedirectUrl: () => string;
  requireDescription: () => string[];
  rssAge: () => number;
  containerWizard: () => { enabled: boolean };

  isSelfServiceUser: () => boolean;
  authenticate: (params: any) => Observable<AuthResponse>;

  acceptAuthentication: () => void;
  logout: () => void;
}

@Injectable({
  providedIn: "root"
})
export class AuthService implements AuthServiceInterface {
  readonly authUrl = environment.proxyUrl + "/auth";

  private readonly http: HttpClient = inject(HttpClient);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  private readonly localService: LocalServiceInterface = inject(LocalService);

  authData = signal<AuthData | null>(null);
  jwtData = signal<JwtData | null>(null);

  authenticationAccepted = signal<boolean>(false);

  isAuthenticated = computed(() => this.authenticationAccepted() && !!this.authData());

  public getHeaders(): HttpHeaders {
    return new HttpHeaders({
      "PI-Authorization": this.localService.getData(BEARER_TOKEN_STORAGE_KEY) || ""
    });
  }

  logLevel = computed(() => this.authData()?.log_level || 0);
  menus = computed(() => this.authData()?.menus || []);
  realm = computed(() => this.jwtData()?.realm || this.authData()?.realm || "");
  rights = computed(() => this.jwtData()?.rights || this.authData()?.rights || []);
  role = computed(() => this.jwtData()?.role || this.authData()?.role || "");
  token = computed(() => this.authData()?.token || "");
  username = computed(() => this.jwtData()?.username || this.authData()?.username || "");
  logoutTimeSeconds = computed(() => {
    const jwtExpDate = this.jwtExpDate()!;
    let jwtLogoutTime: number | null = null;
    const authDataLogoutTime = this.authData()?.logout_time || null;
    if (jwtExpDate) {
      const now = new Date();
      jwtLogoutTime = Math.max(0, Math.floor((jwtExpDate.getTime() - now.getTime()) / 1000));
    }
    if (jwtLogoutTime === null) return authDataLogoutTime;
    if (authDataLogoutTime === null) return jwtLogoutTime;
    return Math.min(jwtLogoutTime, authDataLogoutTime);
  });
  auditPageSize = computed(() => this.authData()?.audit_page_size || 10);
  tokenPageSize = computed(() => this.authData()?.token_page_size || 10);
  userPageSize = computed(() => this.authData()?.user_page_size || 10);
  policyTemplateUrl = computed(() => this.authData()?.policy_template_url || "");
  defaultTokentype = computed(() => this.authData()?.default_tokentype || "");
  defaultContainerType = computed(() => this.authData()?.default_container_type || "");
  userDetails = computed(() => this.authData()?.user_details || false);
  tokenWizard = computed(() => this.authData()?.token_wizard || false);
  tokenWizard2nd = computed(() => this.authData()?.token_wizard_2nd || false);
  adminDashboard = computed(() => this.authData()?.admin_dashboard || false);
  dialogNoToken = computed(() => this.authData()?.dialog_no_token || false);
  searchOnEnter = computed(() => this.authData()?.search_on_enter || false);
  timeoutAction = computed(() => this.authData()?.timeout_action || "logout");
  tokenRollover = computed(() => this.authData()?.token_rollover || {});
  hideWelcome = computed(() => this.authData()?.hide_welcome || false);
  hideButtons = computed(() => this.authData()?.hide_buttons || false);
  deletionConfirmation = computed(() => this.authData()?.deletion_confirmation || false);
  showSeed = computed(() => this.authData()?.show_seed || false);
  showNode = computed(() => this.authData()?.show_node || "");
  subscriptionStatus = computed(() => this.authData()?.subscription_status || 0);
  subscriptionStatusPush = computed(() => this.authData()?.subscription_status_push || 0);
  qrImageAndroid = computed(() => this.authData()?.qr_image_android || null);
  qrImageIOS = computed(() => this.authData()?.qr_image_ios || null);
  qrImageCustom = computed(() => this.authData()?.qr_image_custom || null);
  logoutRedirectUrl = computed(() => this.authData()?.logout_redirect_url || "");
  requireDescription = computed(() => this.authData()?.require_description || []);
  rssAge = computed(() => this.authData()?.rss_age || 0);
  containerWizard = computed(() => this.authData()?.container_wizard || { enabled: false });

  jwtNonce = computed(() => this.jwtData()?.nonce || "");
  authtype = computed(() => (this.jwtData()?.authtype || this.jwtData() ? "cookie" : "none"));
  jwtExpDate = computed(() => {
    const exp = this.jwtData()?.exp;
    return exp ? new Date(exp * 1000) : null;
  });

  isSelfServiceUser = computed(() => {
    return this.role() === "user";
  });

  authenticate(params: any): Observable<AuthResponse> {
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
          this.versioningService.version.set(response.versionnumber);
          const value = response.result?.value;
          if (response?.result?.status && value) {
            this.acceptAuthentication();
            this.authData.set(value);
            this.jwtData.set(this.decodeJwtPayload(value.token));
            this.localService.saveData(BEARER_TOKEN_STORAGE_KEY, value.token);
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
    this.authData.set(null);
    this.jwtData.set(null);
    this.localService.removeData(BEARER_TOKEN_STORAGE_KEY);
    this.authenticationAccepted.set(false);
  }

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
}
