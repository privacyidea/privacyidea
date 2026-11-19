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

import {
  SaveAndExitDialogComponent,
  SaveAndExitDialogResult
} from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { EnrolledTextLink } from "@components/token/token-enrollment/token-enrolled-text/token-enrolled-text.component";
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { DialogServiceInterface } from "@services/dialog/dialog.service";
import { TokenServiceInterface } from "@services/token/token.service";
import { catchError, map, Observable, of, switchMap } from "rxjs";

export type LeaveIncompleteEnrollmentResult = "stay" | "keep" | "deleted";

/**
 * Asks whether to keep or delete the incomplete token before a link leaves an enrollment step.
 * Emits "deleted" only once the token is gone, and "stay" if the user stays or the deletion fails.
 */
export function leaveIncompleteEnrollment(
  dialogService: DialogServiceInterface,
  tokenService: TokenServiceInterface,
  serial: string
): Observable<LeaveIncompleteEnrollmentResult> {
  return dialogService
    .openDialog({
      component: SaveAndExitDialogComponent,
      data: {
        title: $localize`:@@token.leaveIncompleteEnrollment:Leave Incomplete Enrollment`,
        message: $localize`:@@token.leaveIncompleteEnrollmentMessage:The enrollment of this token is not complete. Do you want to keep the incomplete token or delete it before leaving?`,
        saveButtonText: $localize`:@@token.keepToken:Keep Token`,
        discardButtonText: $localize`:@@common.deleteToken:Delete Token`,
        cancelButtonText: $localize`:@@common.back:Back`,
        allowSaveExit: true,
        saveExitDisabled: false
      }
    })
    .afterClosed()
    .pipe(
      switchMap((result: SaveAndExitDialogResult | undefined): Observable<LeaveIncompleteEnrollmentResult> => {
        if (result === "save-exit") {
          return of("keep");
        }
        if (result !== "discard") {
          return of("stay");
        }
        return tokenService.cancelEnrollment(serial).pipe(
          map((): LeaveIncompleteEnrollmentResult => "deleted"),
          catchError(() => of<LeaveIncompleteEnrollmentResult>("stay"))
        );
      })
    );
}

/**
 * Builds the header's confirmLeave for an incomplete enrollment step. It closes the step dialog itself: like
 * Close where Close is offered, otherwise as the user decides. A deleted token's own details stay closed.
 */
export function confirmLeaveIncompleteStep(options: {
  dialogService: DialogServiceInterface;
  tokenService: TokenServiceInterface;
  serial: () => string | undefined;
  canCancel: () => boolean;
  close: (result?: EnrollmentStepResult) => void;
}): (link: EnrolledTextLink) => Observable<boolean> {
  return (link) => {
    const serial = options.serial();
    if (!options.canCancel() || !serial) {
      options.close();
      return of(true);
    }
    return leaveIncompleteEnrollment(options.dialogService, options.tokenService, serial).pipe(
      map((result) => {
        if (result === "stay") {
          return false;
        }
        if (result === "keep") {
          options.close();
          return true;
        }
        options.close(ENROLLMENT_CANCELLED);
        return link !== "token";
      })
    );
  };
}
