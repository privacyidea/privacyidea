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
import { ComponentFixture } from "@angular/core/testing";
import { FIRST_LOAD_GRACE_MS } from "@core/models/table_state/table-state";

/**
 * Waits out the window in which a table draws nothing for its first load, so a test can assert on
 * the placeholder rows and the filter row that appear once a load turns out to be a slow one.
 */
export async function settleFirstLoadGrace(fixture: ComponentFixture<unknown>): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, FIRST_LOAD_GRACE_MS + 20));
  fixture.detectChanges();
}
