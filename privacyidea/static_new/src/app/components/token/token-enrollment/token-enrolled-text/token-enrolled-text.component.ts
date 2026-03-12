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

import { Component, inject, input, output } from "@angular/core";
import { ContentService, ContentServiceInterface } from "../../../../services/content/content.service";

@Component({
  selector: "app-token-enrolled-text",
  imports: [],
  templateUrl: "./token-enrolled-text.component.html",
  styleUrl: "./token-enrolled-text.component.scss"
})
export class TokenEnrolledTextComponent {
  protected readonly contentService: ContentServiceInterface = inject(ContentService);

  serial = input<string>();
  containerSerial = input<string>();
  username = input<string>();
  userRealm = input<string>();
  onlyAddToRealm = input<boolean>();
  rollover = input<boolean>(false);
  switchRoute = output();

  tokenSelected() {
    if (!this.serial()) {
      return;
    }
    this.switchRoute.emit();
    this.contentService.tokenSelected(this.serial() ?? "");
  }

  containerSelected() {
    if (!this.containerSerial()) {
      return;
    }
    this.switchRoute.emit();
    this.contentService.containerSelected(this.containerSerial() ?? "");
  }
}
