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

import { Pipe, PipeTransform } from "@angular/core";

// The accessible names of a column's sort and filter buttons. An interpolated `aria-label="… {{ x }}"` attribute is
// not applied to the element (the buttons rendered without a name), so these pipes feed `[attr.aria-label]`
// instead, with the translation ids and placeholder the template attributes used.
@Pipe({
  name: "sortByLabel",
  standalone: true
})
export class SortByLabelPipe implements PipeTransform {
  transform(label: string): string {
    return $localize`:@@common.sortBy:Sort by ${label}:INTERPOLATION:`;
  }
}

@Pipe({
  name: "filterByLabel",
  standalone: true
})
export class FilterByLabelPipe implements PipeTransform {
  transform(label: string): string {
    return $localize`:@@common.filterBy:Filter by ${label}:INTERPOLATION:`;
  }
}
