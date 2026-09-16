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
import { Component, computed, inject, input } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { AuthenticationLogEntry } from "@services/authentication-log/authentication-log.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";

import { ReasonDetailDialog } from "../../reason-detail-dialog/reason-detail-dialog";
import { parseReasonDetail, ReasonDetail } from "../../reason-detail";

/**
 * The authentication log's Reasons cell: why the request came out the way it did.
 *
 * Every reason the request produced is listed, one line each, so a request whose tokens failed differently shows all
 * of its findings rather than only the top-ranked one. What is *behind* those reasons - which token was found to be
 * what, which policies decided - is a nested map, and it is offered as a dialog (see ReasonDetailDialog) rather than
 * rendered in the row: the log has twelve columns, and neither this one nor the Info column, where it used to be
 * folded into one line of JSON, has room to show it as the table it is.
 */
@Component({
  selector: "app-reason-cell",
  standalone: true,
  imports: [MatButtonModule, MatIcon, MatTooltipModule],
  templateUrl: "./reason-cell.html",
  styleUrl: "./reason-cell.scss"
})
export class ReasonCell {
  // Every reason of the entry, in the backend's own order (see AuthenticationLogReason); empty for a success.
  readonly reasons = input<AuthenticationLogEntry["reasons"]>(null);
  // The entry's other_info, which is where the detail behind those reasons is recorded. The whole record rather than
  // the detail alone, so the table hands the cell a column and this cell owns what it reads out of it.
  readonly info = input<AuthenticationLogEntry["other_info"]>(null);
  // The tokens the attempt was made against, which split the detail's findings (see ReasonDetail). The table passes
  // them for a failed entry only, since it is the one that knows each event type's outcome.
  readonly usedSerials = input<string[]>([]);
  // Named by the dialog where a used token has no finding of its own (see ReasonDetailDialogData).
  readonly eventType = input<string>("");

  private readonly dialogService: DialogServiceInterface = inject(DialogService);

  // Null for an entry whose reasons nobody detailed, which is what leaves the cell without its button.
  readonly detail = computed<ReasonDetail | null>(() => parseReasonDetail(this.info(), this.usedSerials()));

  // A request can end with a detail but no reason of its own: the token that decided the outcome records none when the
  // event type already names the cause - a wrong PIN is logged as PIN_FAIL, and the findings of the tokens the request
  // never got to check are deliberately not promoted to the row (see _note_event in lib/token/auth.py). The cell would
  // then be an empty column beside a lone button, so it says where the answer is instead. Only in that case: a success
  // has neither, and a placeholder on every one of those rows would be noise.
  readonly showsPlaceholder = computed<boolean>(() => !this.reasons()?.length && !!this.detail());

  readonly detailLabel = $localize`Show which token was found to be what`;

  openDetail(detail: ReasonDetail): void {
    this.dialogService.openDialog({
      component: ReasonDetailDialog,
      data: { ...detail, eventType: this.eventType() }
    });
  }
}
