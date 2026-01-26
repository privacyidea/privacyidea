/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { inject } from "@angular/core";
import { CanDeactivateFn } from "@angular/router";
import { PendingChangesService } from "../services/pending-changes/pending-changes.service";
import { MatDialog } from "@angular/material/dialog";
import { map, of } from "rxjs";
import { SimpleConfirmationDialogComponent } from "../components/shared/dialog/confirmation-dialog/confirmation-dialog.component";

export const pendingChangesGuard: CanDeactivateFn<any> = () => {
  const pendingChangesService = inject(PendingChangesService);
  const dialog = inject(MatDialog);

  if (pendingChangesService.hasChanges) {
    return dialog
      .open(SimpleConfirmationDialogComponent, {
        data: {
          title: $localize`Discard changes`,
          action: "discard",
          type: "resolver"
        }
      })
      .afterClosed()
      .pipe(
        map((result) => {
          if (result) {
            // If the user confirms discarding changes, unregister the check
            pendingChangesService.unregisterHasChanges();
            return true;
          }
          return false;
        })
      );
  }

  return of(true);
};
