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
import { FormField } from "@angular/forms/signals";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { TokenTypeConfigForm } from "@components/configuration/token-type-config/token-type-config.form";
import { REMOTE_SERVER } from "@constants/token.constants";

@Component({
  selector: "app-remote-config",
  standalone: true,
  imports: [MatExpansionModule, MatFormFieldModule, MatInputModule, MatCheckboxModule, FormField],
  templateUrl: "./remote-config.component.html"
})
export class RemoteConfigComponent {
  protected readonly REMOTE_SERVER = REMOTE_SERVER;

  config = input.required<TokenTypeConfigForm>();
}
