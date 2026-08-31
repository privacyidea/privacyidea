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
import { DialogAction } from "@models/dialog";

export interface MessageConfirmationDialogData {
  title: string;
  message: string;
  confirmAction: DialogAction<true>;
}

@Component({
  selector: "app-message-confirmation-dialog",
  imports: [DialogWrapperComponent],
  templateUrl: "./message-confirmation-dialog.component.html",
  styleUrl: "./message-confirmation-dialog.component.scss"
})
export class MessageConfirmationDialogComponent extends AbstractDialogComponent<
  MessageConfirmationDialogData,
  boolean
> {
  actions: DialogAction<boolean>[] = [{ ...this.data.confirmAction, primary: this.data.confirmAction.primary ?? true }];

  onAction(value: boolean): void {
    this.close(value);
  }
}
