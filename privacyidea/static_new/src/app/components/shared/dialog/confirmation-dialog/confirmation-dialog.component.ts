// /**
//  * (c) NetKnights GmbH 2025,  https://netknights.it
//  *
//  * This code is free software; you can redistribute it and/or
//  * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
//  * as published by the Free Software Foundation; either
//  * version 3 of the License, or any later version.
//  *
//  * This code is distributed in the hope that it will be useful,
//  * but WITHOUT ANY WARRANTY; without even the implied warranty of
//  * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
//  * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
//  *
//  * You should have received a copy of the GNU Affero General Public
//  * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
//  *
//  * SPDX-License-Identifier: AGPL-3.0-or-later
//  **/
// import { NgClass } from "@angular/common";
// import { Component, inject } from "@angular/core";
// import { MatButton } from "@angular/material/button";
// import {
//   MAT_DIALOG_DATA,
//   MatDialogActions,
//   MatDialogClose,
//   MatDialogContent,
//   MatDialogTitle
// } from "@angular/material/dialog";
// import { DialogWrapperComponent } from "../dialog/dialog-wrapper.component";

// @Component({
//   selector: "app-confirmation-dialog",
//   imports: [
//     MatDialogContent,
//     MatDialogTitle,
//     MatDialogActions,
//     MatButton,
//     MatDialogClose,
//     NgClass,
//     DialogWrapperComponent
//   ],
//   templateUrl: "./confirmation-dialog.component.html",
//   styleUrl: "./confirmation-dialog.component.scss"
// })
// export class ConfirmationDialogComponent {
//   public readonly data: ConfirmationDialogData = inject(MAT_DIALOG_DATA);
// }

// export type DialogAction = "remove" | "delete" | "revoke" | "search" | "unassign" | "";

// export type ConfirmationDialogData = {
//   type: string;
//   title: string;
//   action: DialogAction;
// };

// export type TokenConfirmationDialogData = ConfirmationDialogData & {
//   type: "token";
//   numberOfTokens: string;
//   serialList: string[];
// };
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
import { Component, inject } from "@angular/core";
import { MAT_DIALOG_DATA } from "@angular/material/dialog";
import { DialogWrapperComponent } from "../dialog-wrapper/dialog-wrapper.component";
import { CommonModule } from "@angular/common";
import { ActionType } from "../../../../services/policies/policies.service";
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
export class SimpleConfirmationDialogComponent extends AbstractDialogComponent<SimpleConfirmationDialogData> {
  actions: DialogAction<boolean>[] = [
    ...(this.data.cancelAction ? [this.data.cancelAction] : []),
    this.data.confirmAction
  ];
}

export type SimpleConfirmationDialogData = {
  title: string;
  confirmAction: DialogAction<true>;
  cancelAction?: DialogAction<false>;
  items: string[];
  itemType: string;
};
