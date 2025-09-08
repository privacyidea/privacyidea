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
import { TokenComponent } from "./token.component";
import { MatCardModule } from "@angular/material/card";
import { componentFadeAnimation } from "../../../styles/animations/animations";
import { NavigationSelfServiceComponent } from "./navigation-self-service/navigation-self-service.component";
import { RouterOutlet } from "@angular/router";

@Component({
  selector: "app-token-self-service",
  imports: [MatCardModule, NavigationSelfServiceComponent, RouterOutlet],
  animations: [componentFadeAnimation],
  templateUrl: "./token.self-service.component.html",
  styleUrl: "./token.component.scss"
})
export class TokenSelfServiceComponent extends TokenComponent {
}
