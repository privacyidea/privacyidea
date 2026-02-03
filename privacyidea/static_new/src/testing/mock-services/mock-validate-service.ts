/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Observable, of } from "rxjs";
import { AuthData, AuthDetail, AuthResponse, AuthRole } from "../../app/services/auth/auth.service";
import { ValidateCheckResponse, ValidateServiceInterface } from "../../app/services/validate/validate.service";
import { MockPiResponse } from "./mock-utils";

export class MockAuthData implements AuthData {
  log_level = 0;
  menus = [] as any[];
  realm = "";
  rights = [] as any[];
  role: AuthRole = "" as any;
  token = "";
  username = "";
  logout_time = 0;
  audit_page_size = 10;
  token_page_size = 10;
  user_page_size = 10;
  policy_template_url = "";
  default_tokentype = "";
  default_container_type = "";
  user_details = false;
  token_wizard = false;
  token_wizard_2nd = false;
  admin_dashboard = false;
  dialog_no_token = false;
  search_on_enter = false;
  timeout_action = "";
  token_rollover: any = null;
  hide_welcome = false;
  hide_buttons = false;
  deletion_confirmation = false;
  show_seed = false;
  show_node = "";
  subscription_status = 0;
  subscription_status_push = 0;
  qr_image_android: string | null = null;
  qr_image_ios: string | null = null;
  qr_image_custom: string | null = null;
  logout_redirect_url = "";
  require_description: string[] = [];
  rss_age = 0;
  container_wizard = { enabled: false, type: "", registration: false, template: null } as any;
  versionnumber = "";
}

export class MockAuthDetail implements AuthDetail {
  username = "";
}

export class MockValidateService implements ValidateServiceInterface {
  testToken(_tokenSerial: string, _otpOrPinToTest: string, _otponly?: string): Observable<ValidateCheckResponse> {
    return of({
      id: 1,
      jsonrpc: "2.0",
      result: { status: true, value: true },
      detail: {},
      signature: "",
      time: Date.now(),
      version: "1.0",
      versionnumber: "1.0"
    });
  }

  authenticatePasskey(_args?: { isTest?: boolean }): Observable<AuthResponse> {
    return of(MockPiResponse.fromValue<AuthData, AuthDetail>(new MockAuthData(), new MockAuthDetail()) as any);
  }

  authenticateWebAuthn(_args: { signRequest: any; transaction_id: string; username: string; isTest?: boolean }): Observable<AuthResponse> {
    return of(MockPiResponse.fromValue<AuthData, AuthDetail>(new MockAuthData(), new MockAuthDetail()) as any);
  }

  pollTransaction(_transactionId: string): Observable<boolean> {
    return of(true);
  }
}
