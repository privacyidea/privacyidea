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
import { inject, Injectable } from "@angular/core";
import { MatSnackBar, MatSnackBarRef } from "@angular/material/snack-bar";
import { Subscription, timer } from "rxjs";
import { HttpErrorResponse } from "@angular/common/http";

export interface NotificationServiceInterface {
  remainingTime: number;
  timerSub: Subscription;
  startTime: number;

  success(message: string, options?: { duration?: number }): void;
  error(message: string, options?: { duration?: number }): void;
  warning(message: string, options?: { duration?: number }): void;
  handleResourceError(error: Error | undefined, subject: string): void;
}

@Injectable({
  providedIn: "root"
})
export class NotificationService implements NotificationServiceInterface {
  readonly snackBar = inject(MatSnackBar);
  private _totalDuration: number = 5000;
  remainingTime: number = this._totalDuration;
  timerSub: Subscription = new Subscription();
  startTime: number = 0;

  success(message: string, options?: { duration?: number }): void {
    this._open(message, "success-snackbar", options?.duration);
  }

  error(message: string, options?: { duration?: number }): void {
    this._open(message, "error-snackbar", options?.duration);
  }

  warning(message: string, options?: { duration?: number }): void {
    this._open(message, "warning-snackbar", options?.duration);
  }

  private _open(message: string, panelClass: string, duration?: number): void {
    const totalDuration = duration ?? this._totalDuration;
    const snackBarRef = this.snackBar.open(message, "🗙", {
      horizontalPosition: "center",
      verticalPosition: "bottom",
      duration: undefined,
      panelClass: [panelClass]
    });

    this.remainingTime = totalDuration;
    this.startTime = Date.now();
    this._startTimer(snackBarRef);

    snackBarRef.afterOpened().subscribe(() => {
      const snackBarElement = (snackBarRef.containerInstance as any)._elementRef.nativeElement;
      snackBarElement.addEventListener("mouseenter", () => this._onMouseEnter());
      snackBarElement.addEventListener("mouseleave", () => this._onMouseLeave(snackBarRef));
    });
  }

  private _startTimer<T>(snackBarRef: MatSnackBarRef<T>): void {
    this._clearTimer();
    this.timerSub = timer(this.remainingTime).subscribe(() => {
      snackBarRef.dismiss();
    });
  }

  private _clearTimer(): void {
    if (this.timerSub) {
      this.timerSub.unsubscribe();
    }
  }

  private _onMouseEnter(): void {
    this._clearTimer();
    const elapsed = Date.now() - this.startTime;
    this.remainingTime = Math.max(this.remainingTime - elapsed, 0);
  }

  private _onMouseLeave<T>(snackBarRef: MatSnackBarRef<T>): void {
    if (this.remainingTime > 0) {
      this.startTime = Date.now();
      this._startTimer(snackBarRef);
    }
  }

  handleResourceError(error: Error | undefined, subject: string): void {
    if (error) {
      const err = error as HttpErrorResponse;
      const message = err.error?.result?.error?.message || error.message;
      this.error(`Failed to get ${subject}. ${message}`);
    }
  }
}
