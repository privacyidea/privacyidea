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

import { Directive, inject } from "@angular/core";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { DialogService } from "../../../../services/dialog/dialog.service";

@Directive()
export abstract class AbstractDialogComponent<T = any, R = any> {
  /**
   * The injected data. By initializing it in the constructor, we enforce
   * that any inheriting class must expect this structure (title, content, etc.) in its data.
   */
  public readonly data: T = inject(MAT_DIALOG_DATA);
  protected dialogRef: MatDialogRef<T, R> = inject(MatDialogRef);

  /**
   * Closes the dialog with an optional result.
   * @param dialogResult  - The result to return when the dialog is closed.
   */
  protected close(dialogResult?: R | undefined): void {
    this.dialogRef.close(dialogResult);
  }
}
