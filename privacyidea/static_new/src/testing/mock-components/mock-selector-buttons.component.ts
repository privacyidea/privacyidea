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

@Component({
  selector: "app-selector-buttons",
  standalone: true,
  template: ""
})
export class MockSelectorButtonsComponent<T> {
  readonly initialValue = input.required<T | undefined>();
  readonly values = input.required<T[]>();
  readonly labels = input<T[] | undefined>(undefined);
  readonly allowDeselect = input<boolean>(false);
  readonly disabled = input<boolean>(false);
  readonly valueSelected = output<T | undefined>();
  focusFirst = jest.fn();
}
