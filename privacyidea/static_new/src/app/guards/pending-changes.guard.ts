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
import { CanDeactivateFn, Router } from "@angular/router";
import { PendingChangesService } from "../services/pending-changes/pending-changes.service";
import { SaveAndExitDialogComponent } from "../components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { from, map, of, switchMap } from "rxjs";
import { DialogService, DialogServiceInterface } from "../services/dialog/dialog.service";

export const pendingChangesGuard: CanDeactivateFn<any> = () => {
  const pendingChangesService = inject(PendingChangesService);
  const dialogService: DialogServiceInterface = inject(DialogService);

  if (!pendingChangesService.hasChanges) return of(true);

  const url = inject(Router).url;
  let type = "resolver";
  if (url.includes("smtp")) type = "smtp-server";
  else if (url.includes("tokengroups")) type = "tokengroup";
  else if (url.includes("service-ids")) type = "service-id";
  else if (url.includes("ca-connectors")) type = "ca-connector";
  else if (url.includes("sms")) type = "sms-gateway";
  else if (url.includes("radius")) type = "radius-server";
  else if (url.includes("privacyidea")) type = "privacyidea-server";

  return dialogService
    .openDialog({
      component: SaveAndExitDialogComponent,
      data: {
        title: $localize`Discard changes`,
        message: $localize`You have unsaved changes. Do you want to save them before exiting?`,
        saveExitDisabled: false,
        allowSaveExit: true
      }
    })
    .afterClosed()
    .pipe(
      switchMap((result) => {
        if (result === "discard") {
          pendingChangesService.unregisterHasChanges();
          return of(true);
        }

        if (result === "save-exit") {
          return from(Promise.resolve(pendingChangesService.save())).pipe(
            map(() => {
              pendingChangesService.unregisterHasChanges();
              return true;
            })
          );
        }

        return of(false);
      })
    );
};
