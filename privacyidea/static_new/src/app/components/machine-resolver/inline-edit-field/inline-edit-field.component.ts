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
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";

@Component({
  selector: "app-inline-edit-field",
  templateUrl: "./inline-edit-field.component.html",
  styleUrls: ["./inline-edit-field.component.scss"],
  standalone: true,
  imports: [MatIconButton, MatIcon]
})
export class InlineEditFieldComponent {
  readonly editing = input<boolean>(false);
  readonly showPencil = input<boolean>(false);
  readonly canSave = input<boolean>(false);
  readonly edit = output<void>();
  readonly save = output<void>();
  readonly cancelEdit = output<void>();
}
