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
import { SaveAndExitDialogComponent } from "../components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { from, map, of, switchMap } from "rxjs";
import { DialogService, DialogServiceInterface } from "../services/dialog/dialog.service";

export const pendingChangesGuard: CanDeactivateFn<any> = () => {
  const pendingChangesService = inject(PendingChangesService);
  const dialogService: DialogServiceInterface = inject(DialogService);

  if (!pendingChangesService.hasChanges) return of(true);

  return dialogService
    .openDialog({
      component: SaveAndExitDialogComponent,
      data: {
        saveExitDisabled: !pendingChangesService.validChanges,
        allowSaveExit: true
      }
    })
    .afterClosed()
    .pipe(
      switchMap((result) => {
        if (result === "discard") {
          pendingChangesService.clearAllRegistrations();
          return of(true);
        }

        if (result === "save-exit") {
          const saveResult = pendingChangesService.save();
          return from(Promise.resolve(saveResult)).pipe(
            map((success) => {
              if (success) {
                pendingChangesService.clearAllRegistrations();
              }
              return success;
            })
          );
        }
        return of(false);
      })
    );
};
