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
import { EnrollmentDeviation, formatTimeStep } from "@utils/token.utils";

/** Tells the user which enrolled values differ from the requested ones, because a policy applied in between. */
@Component({
  selector: "app-token-enrollment-policy-deviation-note",
  imports: [],
  templateUrl: "./token-enrollment-policy-deviation-note.component.html"
})
export class TokenEnrollmentPolicyDeviationNoteComponent {
  deviations = input<EnrollmentDeviation[]>([]);
  protected readonly formatTimeStep = formatTimeStep;
}
