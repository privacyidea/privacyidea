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
import { Component, inject, input, signal } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { RouterLink } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { Base64Service, Base64ServiceInterface } from "@services/base64/base64.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { ValidateService, ValidateServiceInterface } from "@services/validate/validate.service";

export interface PasskeyTestResult {
  kind: "success" | "warning";
  message: string;
  mismatch?: { serial: string; username: string; realm?: string };
}

@Component({
  selector: "app-test-passkey-action",
  imports: [MatButtonModule, MatIconModule, RouterLink],
  templateUrl: "./test-passkey-action.component.html",
  styleUrl: "./test-passkey-action.component.scss"
})
export class TestPasskeyActionComponent {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly base64Service: Base64ServiceInterface = inject(Base64Service);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly validateService: ValidateServiceInterface = inject(ValidateService);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  token = input.required<TokenDetails | undefined>();
  readonly result = signal<PasskeyTestResult | null>(null);

  testPasskey(): void {
    this.result.set(null);
    const expectedHash = (this.token()?.info as Record<string, string> | undefined)?.["credential_id_hash"];
    let usedCredentialId: string | null = null;
    this.validateService
      .authenticatePasskey({
        isTest: true,
        onCredentialId: (id) => (usedCredentialId = id)
      })
      .subscribe({
        next: async (checkResponse) => {
          if (!checkResponse.result?.value) {
            this.result.set({ kind: "warning", message: $localize`:@@token.noUserFound:No user found.` });
            return;
          }
          const username = checkResponse.detail?.username ?? $localize`:@@token.unknownUser:Unknown User`;
          const authenticatedSerial = checkResponse.detail?.serial;
          const isAdmin = this.authService.role() === "admin";
          let mismatch = false;
          if (isAdmin && expectedHash && usedCredentialId) {
            const actualHash = await this.sha256HexFromBase64Url(usedCredentialId);
            mismatch = actualHash.toLowerCase() !== expectedHash.toLowerCase();
          }
          if (mismatch) {
            const matchedSerial = authenticatedSerial ?? "";
            this.result.set({
              kind: "warning",
              message: $localize`:@@token.youAuthenticated:You authenticated with a different passkey than the one shown on this page.`,
              mismatch: { serial: matchedSerial, username }
            });
            if (matchedSerial) {
              this.tokenService.getTokenDetails(matchedSerial).subscribe({
                next: (response) => {
                  const realm = response?.result?.value?.tokens?.[0]?.user_realm;
                  const current = this.result();
                  if (current?.mismatch && current.mismatch.serial === matchedSerial && realm) {
                    this.result.set({
                      ...current,
                      mismatch: { ...current.mismatch, realm }
                    });
                  }
                }
              });
            }
          } else {
            this.result.set({
              kind: "success",
              message: $localize`:@@token.authenticationSuccessful:Authentication successful. You would have been logged in as: ${username}:USERNAME:`
            });
          }
        }
      });
  }

  private async sha256HexFromBase64Url(base64Url: string): Promise<string> {
    const bytes = this.base64Service.webAuthnBase64DecToArr(base64Url);
    const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
    const digest = await crypto.subtle.digest("SHA-256", buffer);
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }
}
