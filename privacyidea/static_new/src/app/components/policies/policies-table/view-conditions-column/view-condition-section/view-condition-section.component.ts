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

@Component({
  selector: "app-view-condition-section",
  standalone: true,
  imports: [],
  templateUrl: "./view-condition-section.component.html",
  styleUrls: ["./view-condition-section.component.scss"]
})
export class ViewConditionSectionComponent {
  readonly label = input.required<string>();
  readonly values = input.required<string[]>();
  readonly marker = input<string>();
}
