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

import { Component, computed, inject } from "@angular/core";
import { MatTooltip } from "@angular/material/tooltip";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";

@Component({
  selector: "app-debug-notice",
  standalone: true,
  imports: [MatTooltip],
  templateUrl: "./debug-notice.component.html",
  styleUrl: "./debug-notice.component.scss"
})
export class DebugNoticeComponent {
  private readonly authService: AuthServiceInterface = inject(AuthService);

  readonly visible = computed(() => this.authService.isDebug() && this.authService.role() === "admin");
}
