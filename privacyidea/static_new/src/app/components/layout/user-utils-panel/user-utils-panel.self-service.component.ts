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

import { Component, input } from "@angular/core";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { MatIconButton } from "@angular/material/button";
import { ThemeSwitcherComponent } from "@components/shared/theme-switcher/theme-switcher.component";
import { DatePipe, NgClass } from "@angular/common";
import { UserUtilsPanelComponent } from "@components/layout/user-utils-panel/user-utils-panel.component";

@Component({
  selector: "app-user-utils-panel-self-service",
  imports: [
    MatIcon,
    MatIconButton,
    MatTooltip,
    ThemeSwitcherComponent,
    NgClass,
    DatePipe
  ],
  templateUrl: "./user-utils-panel.self-service.component.html",
  styleUrl: "./user-utils-panel.component.scss"
})
export class UserUtilsPanelSelfServiceComponent extends UserUtilsPanelComponent {
  wizard = input<boolean>(false);
}
