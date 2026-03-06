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
import { Component } from "@angular/core";
import { NavigationSelfServiceButtonComponent } from "./navigation-self-service-button/navigation-self-service-button.component";
import { NavigationSelfServiceComponent } from "./navigation-self-service.component";
import { UserUtilsPanelSelfServiceComponent } from "@components/layout/user-utils-panel/user-utils-panel.self-service.component";

@Component({
  selector: "app-navigation-self-service-wizard",
  standalone: true,
  imports: [NavigationSelfServiceButtonComponent, UserUtilsPanelSelfServiceComponent],
  templateUrl: "./navigation-self-service.wizard.component.html",
  styleUrl: "./navigation-self-service.component.scss"
})
export class NavigationSelfServiceWizardComponent extends NavigationSelfServiceComponent {
}
