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

import { Component, computed, inject, signal } from "@angular/core";
import { MatTooltip } from "@angular/material/tooltip";
import { AuthService, AuthServiceInterface, LogLevel } from "@services/auth/auth.service";

type DebugState = "normal" | "debug" | "debug-passwords";

@Component({
  selector: "app-debug-notice",
  standalone: true,
  imports: [MatTooltip],
  templateUrl: "./debug-notice.component.html",
  styleUrl: "./debug-notice.component.scss"
})
export class DebugNoticeComponent {
  private static readonly DISMISSED_KEY = "piDebugBannerDismissed";

  private readonly authService: AuthServiceInterface = inject(AuthService);

  readonly dismissed = signal(this.readDismissed());
  readonly debugState = computed<DebugState>(() => {
    const level = this.authService.logLevel();
    if (level > LogLevel.Debug) {
      return "normal";
    }
    // lib/log.py writes passwords to the logfile whenever the effective level is below
    // DEBUG (10), and it treats level 0 (NOTSET) the same way, so every level below DEBUG
    // maps to the passwords warning. Level 10 is plain DEBUG with passwords masked.
    return level < LogLevel.Debug ? "debug-passwords" : "debug";
  });
  readonly visible = computed(
    () => this.debugState() !== "normal" && this.authService.role() === "admin" && !this.dismissed()
  );

  dismiss(): void {
    this.dismissed.set(true);
    try {
      sessionStorage.setItem(DebugNoticeComponent.DISMISSED_KEY, "1");
    } catch {
      /* private mode etc. - in-memory only */
    }
  }

  private readDismissed(): boolean {
    try {
      return sessionStorage.getItem(DebugNoticeComponent.DISMISSED_KEY) === "1";
    } catch {
      return false;
    }
  }
}
