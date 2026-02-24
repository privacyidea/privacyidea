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
import { DialogWrapperComponent } from "../dialog-wrapper/dialog-wrapper.component";
import { CommonModule } from "@angular/common";
import { DialogAction } from "../../../../models/dialog";
import { AbstractDialogComponent } from "../abstract-dialog/abstract-dialog.component";

@Component({
  selector: "app-confirmation-dialog",
  imports: [DialogWrapperComponent, CommonModule],
  templateUrl: "./confirmation-dialog.component.html",
  styleUrl: "./confirmation-dialog.component.scss"
})

/**
 * Dialog component used for simple confirmations.
 * * It extends AbstractDialogComponent and requires 'SimpleConfirmationDialogData'
 * which includes a title, a confirm action (required), an optional cancel action,
 * and details about the items being affected.
 * * @see SimpleConfirmationDialogData for required input structure.
 */
export class SimpleConfirmationDialogComponent extends AbstractDialogComponent<SimpleConfirmationDialogData, boolean> {
  actions: DialogAction<boolean>[] = [this.data.confirmAction];
  onAction(value: boolean): void {
    this.close(value);
  }
}

export type SimpleConfirmationDialogData = {
  title: string;
  confirmAction: DialogAction<true>;
  items: string[];
  itemType: string;
};
