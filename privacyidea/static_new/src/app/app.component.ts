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
import { Component, HostListener, inject, OnInit } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { RouterOutlet } from "@angular/router";
import { AuthService, AuthServiceInterface } from "./services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "./services/notification/notification.service";
import { SessionTimerService, SessionTimerServiceInterface } from "./services/session-timer/session-timer.service";

export interface PiResponse<Value, Detail = unknown> {
  id: number;
  jsonrpc: string;
  detail: Detail;
  result?: {
    authentication?: "CHALLENGE" | "POLL" | "PUSH" | "ACCEPT" | "REJECT";
    status: boolean;
    value?: Value;
    error?: {
      code: number;
      message: string;
    };
  };
  signature: string;
  time: number;
  version: string;
  versionnumber: string;
}

/**
 * Checks if a PiResponse indicates a successful authentication.
 *
 * An authentication is considered successful if:
 * - The `result.authentication` property is "ACCEPT".
 * - OR `result.authentication` is not present, AND there is no `detail.multi_challenge`,
 *   AND `result.status` is true, AND `result.value` exists.
 *
 * @param response The `PiResponse` object to check.
 * @returns `true` if the authentication is successful, otherwise `false`.
 */
export function isAuthenticationSuccessful<Value, Detail = unknown>(
  response: PiResponse<Value, Detail>
): response is PiResponse<Value, Detail> & { result: { value: Value; status: true } } {
  if (!response.result) {
    return false;
  }

  // Case 1: result.authentication is "ACCEPT"
  if (response.result.authentication === "ACCEPT") {
    // If authentication is ACCEPT, we must also ensure status is true and value exists
    return response.result.status === true && response.result.value !== undefined;
  }

  // Case 2: result.authentication is not present
  if (response.result.authentication === undefined) {
    const detailWithChallenge = response.detail as { multi_challenge?: unknown[] };
    const isChallengeFree = !detailWithChallenge?.multi_challenge?.length;
    return isChallengeFree && response.result.status && response.result.value !== undefined;
  }
  return false;
}

/**
 * Checks if a PiResponse indicates that a challenge has been triggered.
 *
 * A challenge is considered triggered if:
 * - The `result.authentication` property is "CHALLENGE".
 * - OR `result.authentication` is not present, AND `detail.multi_challenge` exists and is not empty.
 *
 * @param response The `PiResponse` object to check.
 * @returns `true` if a challenge was triggered, otherwise `false`.
 */
export function challengesTriggered<Value, Detail = unknown>(response: PiResponse<Value, Detail>): boolean {
  // Case 1: The response explicitly states a challenge.
  if (response.result?.authentication === "CHALLENGE") {
    return true;
  }

  // Case 2: No explicit authentication status, but a multi_challenge is present.
  if (response.result?.authentication === undefined) {
    const detailWithChallenge = response.detail as { multi_challenge?: unknown[] };
    return !!detailWithChallenge?.multi_challenge?.length;
  }
  return false;
}

@Component({
  selector: "app-root",
  standalone: true,
  imports: [RouterOutlet, FormsModule],
  templateUrl: "./app.component.html",
  styleUrl: "./app.component.scss"
})
export class AppComponent implements OnInit {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly sessionTimerService: SessionTimerServiceInterface = inject(SessionTimerService);

  title = "privacyidea-webui";
  lastSessionReset = 0;

  constructor() {
    this.sessionTimerService.startTimer();

    if (this.authService.isAuthenticated()) {
      console.warn("User is already logged in.");
      this.notificationService.openSnackBar("User is already logged in.");
    }
  }

  ngOnInit(): void {}

  @HostListener("document:click")
  @HostListener("document:keydown")
  @HostListener("document:mousemove")
  @HostListener("document:scroll")
  resetSessionTimer() {
    const now = Date.now();
    if (now - this.lastSessionReset >= 1000) {
      this.lastSessionReset = now;
      this.sessionTimerService.resetTimer();
      this.sessionTimerService.startTimer();
    }
  }
}
