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
import { Component, computed, input } from "@angular/core";
import { FieldTree } from "@angular/forms/signals";

import { MaskedInputComponent } from "../masked-input/masked-input.component";

// The parent owns both fields and passes their FieldTrees. Its schema for the repeated PIN reports the
// `pinMismatch` kind, which this component turns into a message once either field is touched.

@Component({
  selector: "app-enrollment-pin",
  standalone: true,
  imports: [MaskedInputComponent],
  templateUrl: "./enrollment-pin.component.html"
})
export class EnrollmentPinComponent {
  setPinControl = input.required<FieldTree<string>>();
  repeatPinControl = input.required<FieldTree<string>>();

  pinMismatchError = computed(() => {
    const mismatch = this.repeatPinControl()()
      .errors()
      .some((e) => e.kind === "pinMismatch");
    const touched = this.setPinControl()().touched() || this.repeatPinControl()().touched();
    return mismatch && touched ? $localize`:@@common.pinsDoNotMatch:PINs do not match.` : "";
  });
}
