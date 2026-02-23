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

import { DialogServiceInterface } from "../../app/services/dialog/dialog.service";
import { signal } from "@angular/core";
import { of, Subject } from "rxjs";

export class MockDialogService implements DialogServiceInterface {
  isSelfServing = signal<boolean>(false);
  tokenEnrollmentFirstStepRef = null;
  isTokenEnrollmentFirstStepDialogOpen = false;
  tokenEnrollmentLastStepRef = null;
  isTokenEnrollmentLastStepDialogOpen = false;

  private _firstStepAfterClosed$?: Subject<any>;

  openTokenEnrollmentFirstStepDialog = jest.fn().mockImplementation((config?: any) => {
    this.isTokenEnrollmentFirstStepDialogOpen = true;
    this._firstStepAfterClosed$ = new Subject<any>();
    return {
      afterClosed: () => this._firstStepAfterClosed$!.asObservable()
    } as any;
  });

  closeTokenEnrollmentFirstStepDialog = jest.fn().mockImplementation(() => {
    this.isTokenEnrollmentFirstStepDialogOpen = false;
    this._firstStepAfterClosed$?.next(true);
    this._firstStepAfterClosed$?.complete();
  });

  openTokenEnrollmentLastStepDialog = jest.fn().mockImplementation((config?: any) => {
    this.isTokenEnrollmentLastStepDialogOpen = true;
    return {
      afterClosed: () => of(true)
    } as any;
  });

  closeTokenEnrollmentLastStepDialog = jest.fn().mockImplementation(() => {
    this.isTokenEnrollmentLastStepDialogOpen = false;
  });

  confirm = jest.fn().mockResolvedValue(true);
  isAnyDialogOpen = jest.fn().mockReturnValue(false);
}
