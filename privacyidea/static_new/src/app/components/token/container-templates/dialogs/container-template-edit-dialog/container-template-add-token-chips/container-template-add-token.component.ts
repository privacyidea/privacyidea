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

import { Component, input, output } from "@angular/core";

import { MatCardModule } from "@angular/material/card";
import { MatChipListbox, MatChipsModule } from "@angular/material/chips";

import { MatIcon } from "@angular/material/icon";

@Component({
  selector: "app-container-template-add-token",
  standalone: true,
  imports: [MatCardModule, MatChipsModule, MatChipListbox, MatIcon],
  templateUrl: "./container-template-add-token.component.html",
  styleUrls: ["./container-template-add-token.component.scss"]
})
export class ContainerTemplateAddTokenComponent {
  readonly tokenTypes = input.required<string[]>();
  readonly onAddToken = output<string>();

  addToken(tokenType: string) {
    this.onAddToken.emit(tokenType);
  }

  protected _toTitleCase(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
}
