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
import { Component, Input } from "@angular/core";
import { FieldTree, FormField } from "@angular/forms/signals";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";

// TODO: Parent components (e.g. token-enrollment.component.ts) must be updated to pass
// FieldTree<string> instead of FormControl<string> for setPinControl and repeatPinControl,
// and to use validate() on the repeatPin field for cross-field pinMismatch validation
// instead of a FormGroup validator.

@Component({
  selector: "app-enrollment-pin",
  standalone: true,
  imports: [FormField, MatFormField, MatLabel, MatInput, MatError],
  templateUrl: "./enrollment-pin.component.html"
})
export class EnrollmentPinComponent {
  @Input({ required: true }) setPinControl!: FieldTree<string>;
  @Input({ required: true }) repeatPinControl!: FieldTree<string>;
}
