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
import { TestBed } from "@angular/core/testing";

import { NotificationService } from "./notification.service";
import { Subject } from "rxjs";
import { MatSnackBar, MatSnackBarRef } from "@angular/material/snack-bar";

class MockMatSnackBar {
  private afterOpened$ = new Subject<void>();
  private listeners: Record<string, Array<() => void>> = {};

  ref: Pick<MatSnackBarRef<any>, "afterOpened" | "dismiss"> & {
    containerInstance: { _elementRef: { nativeElement: { addEventListener: Function } } };
  } = {
    afterOpened: jest.fn(() => this.afterOpened$.asObservable()),
    dismiss: jest.fn(),
    containerInstance: {
      _elementRef: {
        nativeElement: {
          addEventListener: jest.fn((type: string, cb: () => void) => {
            this.listeners[type] ??= [];
            this.listeners[type].push(cb);
          })
        }
      }
    }
  };

  open = jest.fn((_message: string, _action: string, _config: any) => this.ref);

  emitAfterOpened() {
    this.afterOpened$.next();
  }

  trigger(type: "mouseenter" | "mouseleave") {
    (this.listeners[type] || []).forEach((cb) => cb());
  }
}

describe("NotificationService", () => {
  let service: NotificationService;
  let snackBar: MockMatSnackBar;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date("2025-01-01T00:00:00.000Z"));

    TestBed.configureTestingModule({
      providers: [
        NotificationService,
        { provide: MatSnackBar, useClass: MockMatSnackBar }
      ]
    });

    service = TestBed.inject(NotificationService);
    snackBar = TestBed.inject(MatSnackBar) as unknown as MockMatSnackBar;
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  it("openSnackBar calls MatSnackBar.open and starts a 5s timer", () => {
    service.openSnackBar("Hello");

    expect(snackBar.open).toHaveBeenCalledWith(
      "Hello",
      "🗙",
      expect.objectContaining({ horizontalPosition: "center", verticalPosition: "bottom", duration: undefined })
    );

    jest.advanceTimersByTime(4999);
    expect(snackBar.ref.dismiss).not.toHaveBeenCalled();

    jest.advanceTimersByTime(1);
    expect(snackBar.ref.dismiss).toHaveBeenCalledTimes(1);
  });

  it("adds mouseenter/leave listeners after the snackbar opens", () => {
    service.openSnackBar("Hello");
    expect(snackBar.ref.afterOpened).toHaveBeenCalledTimes(1);

    const addSpy = snackBar.ref.containerInstance._elementRef.nativeElement.addEventListener as jest.Mock;
    expect(addSpy).not.toHaveBeenCalled();

    snackBar.emitAfterOpened();

    expect(addSpy).toHaveBeenCalledWith("mouseenter", expect.any(Function));
    expect(addSpy).toHaveBeenCalledWith("mouseleave", expect.any(Function));
  });

  it("hover pauses the countdown and resume continues from remaining time", () => {
    service.openSnackBar("Snack");
    snackBar.emitAfterOpened();

    jest.advanceTimersByTime(2000);

    snackBar.trigger("mouseenter");
    const remainingAfterHover = service.remainingTime;
    expect(remainingAfterHover).toBeGreaterThanOrEqual(3000 - 5);
    expect(remainingAfterHover).toBeLessThanOrEqual(3000 + 5);

    jest.advanceTimersByTime(remainingAfterHover + 1000);
    expect(snackBar.ref.dismiss).not.toHaveBeenCalled();

    snackBar.trigger("mouseleave");
    expect(snackBar.ref.dismiss).not.toHaveBeenCalled();

    jest.advanceTimersByTime(remainingAfterHover - 1);
    expect(snackBar.ref.dismiss).not.toHaveBeenCalled();

    jest.advanceTimersByTime(1);
    expect(snackBar.ref.dismiss).toHaveBeenCalledTimes(1);
  });

  it("multiple hovers keep pausing/resuming correctly", () => {
    service.openSnackBar("Snack");
    snackBar.emitAfterOpened();

    jest.advanceTimersByTime(1000);
    snackBar.trigger("mouseenter");
    const r1 = service.remainingTime;
    expect(r1).toBeCloseTo(4000, -2);

    snackBar.trigger("mouseleave");
    jest.advanceTimersByTime(500);
    snackBar.trigger("mouseenter");
    const r2 = service.remainingTime;
    expect(r2).toBeLessThan(r1);
    expect(r2).toBeCloseTo(3500, -2);

    snackBar.trigger("mouseleave");
    jest.advanceTimersByTime(r2);
    expect(snackBar.ref.dismiss).toHaveBeenCalledTimes(1);
  });
});
