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
import { DialogServiceInterface } from "@services/dialog/dialog.service";
import { TokenServiceInterface } from "@services/token/token.service";
import { catchError, map, Observable, of, switchMap, takeUntil } from "rxjs";

export type LeaveIncompleteEnrollmentResult = "stay" | "keep" | "deleted";

/**
 * Asks whether to keep or delete the incomplete token before leaving an enrollment step.
 * Emits "deleted" only once the token is gone, and "stay" if the user stays or the deletion fails.
 * The question closes with "stay" once the step closes by itself, e.g. when the push token was registered meanwhile.
 *
 * @param dialogService Opens the question.
 * @param tokenService Deletes the token.
 * @param serial The serial of the incomplete token.
 * @param stepClosed Emits when the step is left without the question.
 * @param deleteWarning Added to the question, what deleting means in this step.
 * @returns What the user chose, once it is done.
 */
export function leaveIncompleteEnrollment(
  dialogService: DialogServiceInterface,
  tokenService: TokenServiceInterface,
  serial: string,
  stepClosed: Observable<unknown>,
  deleteWarning: string | null = null
): Observable<LeaveIncompleteEnrollmentResult> {
  const message = $localize`:@@token.leaveIncompleteEnrollmentMessage:The enrollment of this token is not complete. Do you want to keep the incomplete token or delete it before leaving?`;
  const questionRef = dialogService.openDialog({
    component: SaveAndExitDialogComponent,
    data: {
      title: $localize`:@@token.leaveIncompleteEnrollment:Leave Incomplete Enrollment`,
      message: deleteWarning ? `${message} ${deleteWarning}` : message,
      saveButtonText: $localize`:@@token.keepToken:Keep Token`,
      discardButtonText: $localize`:@@common.deleteToken:Delete Token`,
      cancelButtonText: $localize`:@@common.back:Back`,
      allowSaveExit: true,
      saveExitDisabled: false
    }
  });
  closeWithStep(questionRef, stepClosed);
  return questionRef.afterClosed().pipe(
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
 * Closes an unanswered question asked on top of an enrollment step once the step closes by itself, e.g. when the push
 * token was registered meanwhile. An answer given before that still completes.
 */
export function closeWithStep(
  questionRef: { close: () => void; afterClosed: () => Observable<unknown> },
  stepClosed: Observable<unknown>
): void {
  stepClosed.pipe(takeUntil(questionRef.afterClosed())).subscribe(() => questionRef.close());
}
