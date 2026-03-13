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

import { ComponentRef } from "@angular/core";
import { MatDialogContainer, MatDialogRef, MatDialogState } from "@angular/material/dialog";
import { Subject } from "rxjs";

type PublicPart<T> = { [K in keyof T]: T[K] };

export class MockMatDialogRef<T, R = any> implements PublicPart<MatDialogRef<T, R>> {
  // --- Properties ---
  _containerInstance: MatDialogContainer = {} as MatDialogContainer;
  componentInstance: T = {} as T;
  readonly componentRef: ComponentRef<T> | null = null;
  disableClose: boolean | undefined = undefined;
  id: string = "mock-dialog-ref";

  // --- Internal Subjects for Event Control ---
  private _backdropClick$ = new Subject<MouseEvent>();
  private _keydownEvents$ = new Subject<KeyboardEvent>();
  private _beforeClosed$ = new Subject<R | undefined>();
  private _afterClosed$ = new Subject<R | undefined>();
  private _afterOpened$ = new Subject<void>();

  // --- Mocked Methods ---
  close = jest.fn((result?: R) => {
    this._beforeClosed$.next(result);
    this._beforeClosed$.complete();

    this._afterClosed$.next(result);
    this._afterClosed$.complete();

    // Also complete other subjects to prevent leaks
    this._backdropClick$.complete();
    this._keydownEvents$.complete();
    this._afterOpened$.complete();
  });

  // These methods return observables that stay silent until triggered
  backdropClick = jest.fn().mockReturnValue(this._backdropClick$.asObservable());
  keydownEvents = jest.fn().mockReturnValue(this._keydownEvents$.asObservable());
  beforeClosed = jest.fn().mockReturnValue(this._beforeClosed$.asObservable());
  afterClosed = jest.fn().mockReturnValue(this._afterClosed$.asObservable());
  afterOpened = jest.fn().mockReturnValue(this._afterOpened$.asObservable());

  // Chainable methods
  updateSize = jest.fn().mockReturnThis();
  updatePosition = jest.fn().mockReturnThis();
  addPanelClass = jest.fn().mockReturnThis();
  removePanelClass = jest.fn().mockReturnThis();

  getState = jest.fn().mockReturnValue(MatDialogState.OPEN);

  // --- Helper Methods for Unit Tests ---
  /**
   * Manually trigger a backdrop click event
   */
  fireBackdropClick(): void {
    this._backdropClick$.next(new MouseEvent("click"));
  }

  /**
   * Manually trigger a keydown event (e.g., ESC key)
   */
  fireKeydownEvent(event: KeyboardEvent): void {
    this._keydownEvents$.next(event);
  }

  /**
   * Manually signal that the dialog has finished opening
   */
  fireAfterOpened(): void {
    this._afterOpened$.next();
  }
}
