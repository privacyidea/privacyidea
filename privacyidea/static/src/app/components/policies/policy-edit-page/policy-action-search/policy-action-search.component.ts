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

import { Component, model } from "@angular/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";

/**
 * The search field for policy actions. It filters both action panels, and is rendered either at
 * the top of the actions tab or, while the page header is pinned, inside that header - so it lives
 * in two places and keeps no state of its own.
 */
@Component({
  selector: "app-policy-action-search",
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, ClearableInputComponent],
  templateUrl: "./policy-action-search.component.html",
  styleUrl: "./policy-action-search.component.scss"
})
export class PolicyActionSearchComponent {
  readonly actionFilter = model<string>("");
}
