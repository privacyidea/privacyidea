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
import { NgOptimizedImage } from "@angular/common";
import { Component, computed, inject } from "@angular/core";
import { environment } from "@env/environment";
import { ConfigService } from "@services/config/config.service";

/** The logo shown above the forms of the login page and the password recovery pages. */
@Component({
  selector: "app-login-logo",
  standalone: true,
  imports: [NgOptimizedImage],
  templateUrl: "./login-logo.component.html",
  styleUrl: "./login-logo.component.scss"
})
export class LoginLogoComponent {
  private readonly configService = inject(ConfigService);

  customLogo = computed(() => {
    if (!this.configService.config()?.logo) {
      return null;
    }
    return environment.proxyUrl + "/static/public/" + this.configService.config()?.logo;
  });
}
