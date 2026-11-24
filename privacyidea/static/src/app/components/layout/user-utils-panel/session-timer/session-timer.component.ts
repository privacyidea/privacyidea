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
import { DatePipe, NgClass } from "@angular/common";
import { Component, computed, inject } from "@angular/core";
import { MatTooltip } from "@angular/material/tooltip";
import { SessionTimerService, SessionTimerServiceInterface } from "@services/session-timer/session-timer.service";

const TEN_MINUTES_MS = 600_000;
const ONE_HOUR_MS = 3_600_000;

@Component({
  selector: "app-session-timer",
  imports: [MatTooltip, NgClass, DatePipe],
  templateUrl: "./session-timer.component.html",
  styleUrl: "./session-timer.component.scss"
})
export class SessionTimerComponent {
  protected readonly sessionTimerService: SessionTimerServiceInterface = inject(SessionTimerService);

  /**
   * The displayed time rounded up to the minute, once minutes are the smallest unit shown.
   *
   * The formats below change at whole hours and at ten minutes, and a session length set to exactly
   * one of those - 3600 seconds, say - resets the countdown to sit exactly on the boundary. Reading
   * the raw value there flips the format on the first tick after every reset, and back on the next
   * activity, which changes the width of the panel. Rounding up keeps the value on one side of the
   * boundary until it has genuinely passed it.
   */
  protected readonly displayedTime = computed(() => {
    const remaining = this.sessionTimerService.remainingTime() ?? 0;
    // Below ten minutes the seconds are on show, so the value is used as it is.
    if (remaining < TEN_MINUTES_MS) {
      return remaining;
    }
    return Math.ceil(remaining / 60_000) * 60_000;
  });

  sessionTimeFormat = computed(() => {
    // Use non-breaking half space (U+202F) between number and unit
    if (this.displayedTime() < TEN_MINUTES_MS) {
      // less than 10 minutes remaining, show minutes and seconds
      return "m:ss";
    } else if (this.displayedTime() < ONE_HOUR_MS) {
      // less than an hour, show only minutes
      return "m'\u202Fmin'";
    }
    // show hours and minutes
    return "H'\u202Fh' mm'\u202Fmin'";
  });

  // Once more than a day remains, the DatePipe format above can no longer
  // represent the duration, so show days (and any whole hours) without minutes.
  sessionOverOneDay = computed(() => this.displayedTime() >= 86_400_000);

  sessionDaysText = computed(() => {
    const ms = this.displayedTime();
    const days = Math.floor(ms / 86_400_000);
    const hours = Math.floor((ms % 86_400_000) / 3_600_000);
    // Non-breaking half space (U+202F) between number and unit, matching the
    // hour/minute format above.
    return hours > 0 ? `${days}\u202Fd ${hours}\u202Fh` : `${days}\u202Fd`;
  });
}
