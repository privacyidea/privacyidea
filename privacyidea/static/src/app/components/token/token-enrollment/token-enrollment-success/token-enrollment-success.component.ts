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
import { Component, computed, inject, signal } from "@angular/core";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { MessageConfirmationDialogComponent } from "@components/shared/dialog/message-confirmation-dialog/message-confirmation-dialog.component";
import { EnrollmentStep } from "@components/token/token-enrollment/enrollment-step";
import { TokenEnrollmentDataComponent } from "@components/token/token-enrollment/token-enrollment-data/token-enrollment-data.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { map, Observable, of } from "rxjs";

// The enrolled token with its enrollment data.
@Component({
  selector: "app-token-enrollment-success",
  templateUrl: "./token-enrollment-success.component.html",
  imports: [TokenEnrollmentDataComponent]
})
export class TokenEnrollmentSuccessComponent extends EnrollmentStep {
  protected readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly rollover = this.data.rollover ?? false;

  readonly title = computed(() =>
    this.rollover
      ? $localize`:@@token.tokenSuccessfullyRolled:Token Successfully Rolled Over`
      : $localize`:@@token.tokenSuccessfully:Token Successfully Enrolled`
  );
  readonly headerState = "done";

  // What closing would leave unsaved, so the dialog asks first; empty closes right away.
  private readonly closeConfirmation = signal("");

  override confirmClose(confirmLabel = $localize`:@@common.close:Close`): Observable<boolean> {
    const message = this.closeConfirmation();
    if (!message) {
      return of(true);
    }
    return this.dialogService
      .openDialog({
        component: MessageConfirmationDialogComponent,
        data: {
          title: $localize`:@@token.enrollmentDataNotSaved:Enrollment Data Not Saved`,
          message,
          confirmAction: { label: confirmLabel, value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .pipe(map((confirmed) => !!confirmed));
  }

  onCloseConfirmationChange(message: string): void {
    this.closeConfirmation.set(message);
  }

  onEnrollmentResponseChange(response: EnrollmentResponse): void {
    this.data.onEnrollmentResponseChange?.(response);
  }
}
