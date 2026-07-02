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
import { HttpErrorResponse } from "@angular/common/http";
import { ElementRef, inject, Injectable } from "@angular/core";
import { MatSnackBar, MatSnackBarRef } from "@angular/material/snack-bar";
import { Subscription, timer } from "rxjs";

export type NotificationSeverity = "success" | "warning" | "error";

interface QueuedNotification {
  severity: NotificationSeverity;
  message: string;
  duration?: number;
}

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
  private readonly snackBar = inject(MatSnackBar);
  private readonly _debounceMs = 200;
  private readonly _maxBatchedDuration = 15000;
  private _totalDuration = 5000;
  private _queue: QueuedNotification[] = [];
  private _flushTimer: ReturnType<typeof setTimeout> | undefined;

  remainingTime: number = this._totalDuration;
  timerSub = new Subscription();
  startTime = 0;

  success(message: string, options?: { duration?: number }): void {
    this._enqueue("success", message, options?.duration);
  }

  error(message: string, options?: { duration?: number }): void {
    this._enqueue("error", message, options?.duration);
  }

  warning(message: string, options?: { duration?: number }): void {
    this._enqueue("warning", message, options?.duration);
  }

  handleResourceError(error: Error | undefined, subject: string): void {
    if (error) {
      const err = error as HttpErrorResponse;
      const message = err.error?.result?.error?.message || error.message;
      this.error(`Failed to get ${subject}. ${message}`);
    }
  }

  private _enqueue(severity: NotificationSeverity, message: string, duration?: number): void {
    this._queue.push({ severity, message, duration });
    if (this._flushTimer !== undefined) {
      clearTimeout(this._flushTimer);
    }
    this._flushTimer = setTimeout(() => this._flush(), this._debounceMs);
  }

  private _flush(): void {
    this._flushTimer = undefined;
    if (this._queue.length === 0) return;

    const queue = this._queue;
    this._queue = [];

    if (queue.length === 1) {
      const m = queue[0];
      this._open(m.message, `${m.severity}-snackbar`, m.duration);
      return;
    }

    const order: NotificationSeverity[] = ["error", "warning", "success"];
    const groups = new Map<NotificationSeverity, string[]>();
    for (const sev of order) groups.set(sev, []);
    for (const m of queue) groups.get(m.severity)!.push(m.message);

    const highest = order.find((s) => groups.get(s)!.length > 0)!;

    const sections: string[] = [];
    for (const sev of order) {
      const msgs = groups.get(sev)!;
      if (msgs.length === 0) continue;
      sections.push(this._headerFor(sev, msgs.length));
      for (const msg of msgs) sections.push(`• ${msg}`);
    }

    const baseDuration = Math.max(...queue.map((m) => m.duration ?? this._totalDuration));
    const totalDuration = Math.min(baseDuration + (queue.length - 1) * 500, this._maxBatchedDuration);

    this._open(sections.join("\n"), `${highest}-snackbar`, totalDuration);
  }

  private _headerFor(severity: NotificationSeverity, count: number): string {
    if (severity === "error") {
      return count === 1 ? $localize`1 error:` : $localize`${count} errors:`;
    }
    if (severity === "warning") {
      return count === 1 ? $localize`1 warning:` : $localize`${count} warnings:`;
    }
    return count === 1 ? $localize`1 success:` : $localize`${count} successes:`;
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
      const snackBarElement = (snackBarRef.containerInstance as unknown as { _elementRef: ElementRef<HTMLElement> })
        ._elementRef.nativeElement;
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
}
