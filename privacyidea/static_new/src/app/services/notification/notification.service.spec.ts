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
import { TestBed } from "@angular/core/testing";

import { MatSnackBar, MatSnackBarConfig, MatSnackBarRef } from "@angular/material/snack-bar";
import { Subject } from "rxjs";
import { NotificationService } from "./notification.service";

class MockMatSnackBar {
  private afterOpened$ = new Subject<void>();
  private listeners: Record<string, (() => void)[]> = {};

  ref: Pick<MatSnackBarRef<unknown>, "afterOpened" | "dismiss"> & {
    containerInstance: { _elementRef: { nativeElement: { addEventListener: (type: string, cb: () => void) => void } } };
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

  open = jest.fn<MockMatSnackBar["ref"], [string, string, MatSnackBarConfig]>(() => this.ref);

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
  let totalDuration: number;
  let debounceMs: number;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(Date.parse("2025-01-01T00:00:00.000Z"));

    TestBed.configureTestingModule({
      providers: [NotificationService, { provide: MatSnackBar, useClass: MockMatSnackBar }]
    });

    service = TestBed.inject(NotificationService);
    snackBar = TestBed.inject(MatSnackBar) as unknown as MockMatSnackBar;
    // Override the large default duration with a testable value
    totalDuration = 5000;
    const privates = service as unknown as { _totalDuration: number; _debounceMs: number };
    privates._totalDuration = totalDuration;
    service.remainingTime = totalDuration;
    debounceMs = privates._debounceMs;
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  const flushDebounce = () => jest.advanceTimersByTime(debounceMs);

  describe.each([
    { method: "success" as const, panelClass: "success-snackbar" },
    { method: "error" as const, panelClass: "error-snackbar" },
    { method: "warning" as const, panelClass: "warning-snackbar" }
  ])("$method()", ({ method, panelClass }) => {
    it("calls MatSnackBar.open with correct config after debounce", () => {
      service[method]("Test message");
      expect(snackBar.open).not.toHaveBeenCalled();

      flushDebounce();

      expect(snackBar.open).toHaveBeenCalledWith(
        "Test message",
        "🗙",
        expect.objectContaining({
          horizontalPosition: "center",
          verticalPosition: "bottom",
          duration: undefined,
          panelClass: [panelClass]
        })
      );
    });

    it("dismisses after the full duration", () => {
      service[method]("Hello");
      flushDebounce();

      jest.advanceTimersByTime(totalDuration - 1);
      expect(snackBar.ref.dismiss).not.toHaveBeenCalled();

      jest.advanceTimersByTime(1);
      expect(snackBar.ref.dismiss).toHaveBeenCalledTimes(1);
    });

    it("adds mouseenter/leave listeners after the snackbar opens", () => {
      service[method]("Hello");
      flushDebounce();
      expect(snackBar.ref.afterOpened).toHaveBeenCalledTimes(1);

      const addSpy = snackBar.ref.containerInstance._elementRef.nativeElement.addEventListener as jest.Mock;
      expect(addSpy).not.toHaveBeenCalled();

      snackBar.emitAfterOpened();

      expect(addSpy).toHaveBeenCalledWith("mouseenter", expect.any(Function));
      expect(addSpy).toHaveBeenCalledWith("mouseleave", expect.any(Function));
    });

    it("hover pauses the countdown and resume continues from remaining time", () => {
      service[method]("Snack");
      flushDebounce();
      snackBar.emitAfterOpened();

      jest.advanceTimersByTime(2000);

      snackBar.trigger("mouseenter");
      const remainingAfterHover = service.remainingTime;
      expect(remainingAfterHover).toBeCloseTo(totalDuration - 2000, -2);

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
      service[method]("Snack");
      flushDebounce();
      snackBar.emitAfterOpened();

      jest.advanceTimersByTime(1000);
      snackBar.trigger("mouseenter");
      const r1 = service.remainingTime;
      expect(r1).toBeCloseTo(totalDuration - 1000, -2);

      snackBar.trigger("mouseleave");
      jest.advanceTimersByTime(500);
      snackBar.trigger("mouseenter");
      const r2 = service.remainingTime;
      expect(r2).toBeLessThan(r1);
      expect(r2).toBeCloseTo(totalDuration - 1500, -2);

      snackBar.trigger("mouseleave");
      jest.advanceTimersByTime(r2);
      expect(snackBar.ref.dismiss).toHaveBeenCalledTimes(1);
    });
  });

  it("resets the timer when a new notification opens after the previous flushed", () => {
    service.success("First");
    flushDebounce();
    jest.advanceTimersByTime(2000);

    service.error("Second");
    flushDebounce();
    expect(service.remainingTime).toBe(totalDuration);

    jest.advanceTimersByTime(totalDuration - 1);
    expect(snackBar.ref.dismiss).not.toHaveBeenCalled();

    jest.advanceTimersByTime(1);
    expect(snackBar.ref.dismiss).toHaveBeenCalled();
  });

  it("each method passes a distinct panelClass", () => {
    service.success("s");
    flushDebounce();
    const successCall = snackBar.open.mock.calls[0][2];
    expect(successCall["panelClass"]).toEqual(["success-snackbar"]);

    service.error("e");
    flushDebounce();
    const errorCall = snackBar.open.mock.calls[1][2];
    expect(errorCall["panelClass"]).toEqual(["error-snackbar"]);

    service.warning("w");
    flushDebounce();
    const warningCall = snackBar.open.mock.calls[2][2];
    expect(warningCall["panelClass"]).toEqual(["warning-snackbar"]);
  });

  describe("batching", () => {
    it("coalesces multiple errors within the debounce window into one snackbar", () => {
      service.error("First error");
      service.error("Second error");
      service.error("Third error");

      expect(snackBar.open).not.toHaveBeenCalled();

      flushDebounce();

      expect(snackBar.open).toHaveBeenCalledTimes(1);
      const [message, , config] = snackBar.open.mock.calls[0];
      expect(message).toContain("3 errors:");
      expect(message).toContain("• First error");
      expect(message).toContain("• Second error");
      expect(message).toContain("• Third error");
      expect(config["panelClass"]).toEqual(["error-snackbar"]);
    });

    it("extends the debounce window when new notifications arrive", () => {
      service.error("A");
      jest.advanceTimersByTime(debounceMs - 1);
      service.error("B");

      // First window would have flushed if not extended
      jest.advanceTimersByTime(1);
      expect(snackBar.open).not.toHaveBeenCalled();

      jest.advanceTimersByTime(debounceMs);
      expect(snackBar.open).toHaveBeenCalledTimes(1);
      const message = snackBar.open.mock.calls[0][0];
      expect(message).toContain("• A");
      expect(message).toContain("• B");
    });

    it("groups mixed-severity batches under separate headers and uses highest severity panel", () => {
      service.success("Saved");
      service.warning("Almost full");
      service.error("Boom");
      flushDebounce();

      expect(snackBar.open).toHaveBeenCalledTimes(1);
      const [message, , config] = snackBar.open.mock.calls[0];
      expect(config["panelClass"]).toEqual(["error-snackbar"]);
      // Headers appear in severity order: error → warning → success
      const errorIdx = message.indexOf("1 error:");
      const warningIdx = message.indexOf("1 warning:");
      const successIdx = message.indexOf("1 success:");
      expect(errorIdx).toBeGreaterThanOrEqual(0);
      expect(warningIdx).toBeGreaterThan(errorIdx);
      expect(successIdx).toBeGreaterThan(warningIdx);
      expect(message).toContain("• Boom");
      expect(message).toContain("• Almost full");
      expect(message).toContain("• Saved");
    });

    it("uses singular header for a single non-coalesced batch entry per severity", () => {
      service.error("Only one");
      service.warning("Only one warn");
      flushDebounce();
      const message = snackBar.open.mock.calls[0][0];
      expect(message).toContain("1 error:");
      expect(message).toContain("1 warning:");
    });

    it("extends duration for larger batches but caps at the max", () => {
      for (let i = 0; i < 30; i++) service.error(`err ${i}`);
      flushDebounce();
      const max = (service as unknown as { _maxBatchedDuration: number })._maxBatchedDuration;
      expect(service.remainingTime).toBe(max);
    });

    it("does not batch when calls are separated by more than the debounce window", () => {
      service.error("First");
      flushDebounce();
      expect(snackBar.open).toHaveBeenCalledTimes(1);
      expect(snackBar.open.mock.calls[0][0]).toBe("First");

      // Let the first snackbar dismiss so we don't conflate timers
      jest.advanceTimersByTime(totalDuration);

      service.error("Second");
      flushDebounce();
      expect(snackBar.open).toHaveBeenCalledTimes(2);
      expect(snackBar.open.mock.calls[1][0]).toBe("Second");
    });
  });
});
