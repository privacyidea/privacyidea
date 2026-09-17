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
import { Component, input, signal } from "@angular/core";
import { FieldTree, FormField } from "@angular/forms/signals";
import { MatIconButton } from "@angular/material/button";
import { MatError, MatFormField, MatHint, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";

@Component({
  selector: "app-masked-input",
  standalone: true,
  imports: [FormField, MatFormField, MatLabel, MatInput, MatIconButton, MatIcon, MatSuffix, MatHint, MatError],
  templateUrl: "./masked-input.component.html",
  styleUrls: ["./masked-input.component.scss"]
})
export class MaskedInputComponent {
  field = input.required<FieldTree<string>>();
  label = input.required<string>();
  placeholder = input("");
  hint = input("");
  error = input("");
  masked = signal(true);

  toggleMasked(): void {
    this.masked.update((masked) => !masked);
  }
}
