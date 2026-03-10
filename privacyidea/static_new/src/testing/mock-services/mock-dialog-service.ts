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

import { DialogServiceInterface } from "../../app/services/dialog/dialog.service";
import { MockMatDialogRef } from "../mock-mat-dialog-ref";

export class MockDialogService implements DialogServiceInterface {
  private lastDialogRef: any = null;

  closeDialog = jest.fn().mockImplementation((dialogRef) => {
    if (this.lastDialogRef === dialogRef) {
      this.lastDialogRef = null;
    }
    return true;
  });

  openDialog = jest.fn().mockImplementation(() => {
    this.lastDialogRef = new MockMatDialogRef();
    return this.lastDialogRef;
  });

  openDialogAsync = jest.fn().mockResolvedValue(true);

  closeLatestDialog = jest.fn().mockImplementation(() => {
    this.lastDialogRef = null;
  });

  closeAllDialogs = jest.fn().mockImplementation(() => {
    this.lastDialogRef = null;
  });

  isDialogOpen = jest.fn().mockImplementation((dialogRef) => {
    return this.lastDialogRef === dialogRef && this.lastDialogRef !== null;
  });

  isAnyDialogOpen = jest.fn().mockImplementation(() => {
    return this.lastDialogRef !== null;
  });

  confirm = jest.fn().mockResolvedValue(true);
}
