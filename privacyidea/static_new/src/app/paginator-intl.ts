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
  intl.itemsPerPageLabel = $localize`:@@nav.itemsPerPage:Items per page:`;
  intl.nextPageLabel = $localize`:@@nav.nextPage:Next page`;
  intl.previousPageLabel = $localize`:@@nav.previousPage:Previous page`;
  intl.firstPageLabel = $localize`:@@nav.firstPage:First page`;
  intl.lastPageLabel = $localize`:@@nav.lastPage:Last page`;
  intl.getRangeLabel = (page: number, pageSize: number, length: number): string => {
    if (length === 0 || pageSize === 0) {
      return $localize`:@@nav.of:0 of ${length}:LENGTH:`;
    }
    length = Math.max(length, 0);
    const startIndex = page * pageSize;
    const endIndex = startIndex < length ? Math.min(startIndex + pageSize, length) : startIndex + pageSize;
    return $localize`:@@nav.pageRange:${startIndex + 1}:START: – ${endIndex}:END: of ${length}:LENGTH:`;
  };
  return intl;
}
