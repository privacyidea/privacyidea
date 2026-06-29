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
import { MatPaginatorIntl } from "@angular/material/paginator";

/**
 * MatPaginatorIntl whose labels are localized via $localize. Angular Material
 * ships these strings in English only; without this factory the paginator
 * ("Items per page", range label, navigation buttons) stays untranslated.
 */
export function createPaginatorIntl(): MatPaginatorIntl {
  const intl = new MatPaginatorIntl();
  intl.itemsPerPageLabel = $localize`Items per page:`;
  intl.nextPageLabel = $localize`Next page`;
  intl.previousPageLabel = $localize`Previous page`;
  intl.firstPageLabel = $localize`First page`;
  intl.lastPageLabel = $localize`Last page`;
  intl.getRangeLabel = (page: number, pageSize: number, length: number): string => {
    if (length === 0 || pageSize === 0) {
      return $localize`0 of ${length}`;
    }
    length = Math.max(length, 0);
    const startIndex = page * pageSize;
    const endIndex = startIndex < length ? Math.min(startIndex + pageSize, length) : startIndex + pageSize;
    return $localize`${startIndex + 1} – ${endIndex} of ${length}`;
  };
  return intl;
}
