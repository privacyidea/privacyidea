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
import { Component } from "@angular/core";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";

import { ReasonDetail } from "../reason-detail";

/**
 * What is behind one authentication-log entry's reasons: which of the user's tokens was found to be what, and which
 * policies decided the request.
 *
 * Opened from the Reasons column (see ReasonCell) rather than shown in the Info column, which is where the same data
 * used to be read as a one-line JSON dump. A dialog is what buys it a shape: the per-serial findings are a table of
 * serial and reason, which is how an admin reads them - "which token failed, and why" - and a table is exactly what
 * the twelve-column log has no room for.
 *
 * Read-only, so it closes rather than returning anything.
 */
@Component({
  selector: "app-reason-detail-dialog",
  standalone: true,
  imports: [DialogWrapperComponent],
  templateUrl: "./reason-detail-dialog.html",
  styleUrl: "./reason-detail-dialog.scss"
})
export class ReasonDetailDialog extends AbstractDialogComponent<ReasonDetail> {}
