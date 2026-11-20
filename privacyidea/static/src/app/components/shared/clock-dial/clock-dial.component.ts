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
import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  input,
  output,
  signal,
  viewChild
} from "@angular/core";

/** A wall-clock time of day, 24h. */
export interface ClockTime {
  hour: number;
  minute: number;
}

export type ClockDialView = "hours" | "minutes";

// The dial is drawn in a CLOCK_DIAL_SIZE square viewBox, pointer positions are scaled into it. Hours 1-12 sit on the
// outer ring, 13-23 and 0 on the inner ring (like the 24h alarm clock on Android), minutes on the outer ring.
export const CLOCK_DIAL_SIZE = 256;
export const CLOCK_OUTER_RADIUS = 104;
export const CLOCK_INNER_RADIUS = 68;
const CENTER = CLOCK_DIAL_SIZE / 2;
const RING_BORDER = (CLOCK_OUTER_RADIUS + CLOCK_INNER_RADIUS) / 2;

interface DialMark {
  value: number;
  text: string;
  x: number;
  y: number;
  inner: boolean;
  disabled: boolean;
  selected: boolean;
}

/** Clockwise angle of a point from 12 o'clock, in degrees 0..360. */
function angleAt(x: number, y: number): number {
  const degrees = (Math.atan2(x - CENTER, CENTER - y) * 180) / Math.PI;
  return (degrees + 360) % 360;
}

function pointAt(degrees: number, radius: number): { x: number; y: number } {
  const rad = (degrees * Math.PI) / 180;
  return { x: CENTER + radius * Math.sin(rad), y: CENTER - radius * Math.cos(rad) };
}

/** The hour under a point of the dial: the angle picks the clock position, the distance from the centre the ring. */
export function hourAtPoint(x: number, y: number): number {
  const position = Math.round(angleAt(x, y) / 30) % 12;
  const inner = Math.hypot(x - CENTER, y - CENTER) < RING_BORDER;
  if (inner) {
    return position === 0 ? 0 : position + 12;
  }
  return position === 0 ? 12 : position;
}

/** The minute under a point of the dial, any of 0..59, wherever the distance from the centre. */
export function minuteAtPoint(x: number, y: number): number {
  return Math.round(angleAt(x, y) / 6) % 60;
}

export function formatClockTime(time: ClockTime): string {
  return `${String(time.hour).padStart(2, "0")}:${String(time.minute).padStart(2, "0")}`;
}

function isInnerHour(hour: number): boolean {
  return hour === 0 || hour > 12;
}

function hourPoint(hour: number): { x: number; y: number } {
  return pointAt((hour % 12) * 30, isInnerHour(hour) ? CLOCK_INNER_RADIUS : CLOCK_OUTER_RADIUS);
}

/**
 * Clock face time picker: first the hour on a two-ring 24h dial, then (automatically) the minute. Tap or drag on the
 * dial, or use the arrow keys (PageUp/PageDown step 5 minutes) and Enter. Picking the minute emits `selected`.
 * Times before `min` are greyed out and cannot be picked, so a caller can rule out an end before a start.
 */
@Component({
  selector: "app-clock-dial",
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./clock-dial.component.html",
  styleUrl: "./clock-dial.component.scss",
  host: {
    role: "dialog",
    "[attr.aria-label]": "label()"
  }
})
export class ClockDialComponent {
  readonly label = input.required<string>();
  readonly min = input<ClockTime | null>(null);
  readonly selected = output<ClockTime>();

  readonly hour = signal<number | null>(null);
  readonly minute = signal<number | null>(null);
  readonly view = signal<ClockDialView>("hours");

  protected readonly size = CLOCK_DIAL_SIZE;
  protected readonly center = CENTER;
  protected readonly hourLabel = $localize`:@@clockDial.hour:Hour`;
  protected readonly minuteLabel = $localize`:@@clockDial.minute:Minute`;
  private readonly face = viewChild.required<ElementRef<HTMLElement>>("face");
  private dragging = false;

  protected readonly hourText = computed(() => {
    const hour = this.hour();
    return hour === null ? "--" : String(hour).padStart(2, "0");
  });
  protected readonly minuteText = computed(() => {
    const minute = this.minute();
    return minute === null ? "--" : String(minute).padStart(2, "0");
  });
  protected readonly value = computed(() => (this.view() === "hours" ? this.hour() : this.minute()));

  protected readonly marks = computed<DialMark[]>(() => {
    if (this.view() === "hours") {
      const hour = this.hour();
      return Array.from({ length: 24 }, (_, value) => ({
        value,
        text: value === 0 ? "00" : String(value),
        ...hourPoint(value),
        inner: isInnerHour(value),
        disabled: this.isHourDisabled(value),
        selected: value === hour
      }));
    }
    const minute = this.minute();
    return Array.from({ length: 12 }, (_, index) => {
      const value = index * 5;
      return {
        value,
        text: String(value).padStart(2, "0"),
        ...pointAt(value * 6, CLOCK_OUTER_RADIUS),
        inner: false,
        disabled: this.isMinuteDisabled(value),
        selected: value === minute
      };
    });
  });

  /** Where the hand points: the selected value of the current view, or nothing yet. */
  protected readonly hand = computed(() => {
    if (this.view() === "hours") {
      const hour = this.hour();
      return hour === null ? null : { ...hourPoint(hour), inner: isInnerHour(hour), between: false };
    }
    const minute = this.minute();
    return minute === null
      ? null
      : { ...pointAt(minute * 6, CLOCK_OUTER_RADIUS), inner: false, between: minute % 5 !== 0 };
  });

  constructor() {
    afterNextRender(() => this.face().nativeElement.focus());
  }

  isHourDisabled(hour: number): boolean {
    const min = this.min();
    return !!min && hour < min.hour;
  }

  isMinuteDisabled(minute: number): boolean {
    const min = this.min();
    const hour = this.hour();
    return !!min && (hour === null || hour === min.hour) && minute < min.minute;
  }

  showHours(): void {
    this.view.set("hours");
  }

  showMinutes(): void {
    if (this.hour() !== null) {
      this.view.set("minutes");
    }
  }

  protected onPointerDown(event: PointerEvent): void {
    event.preventDefault();
    this.dragging = true;
    (event.target as Element | null)?.setPointerCapture?.(event.pointerId);
    this.trackPointer(event);
  }

  protected onPointerMove(event: PointerEvent): void {
    if (this.dragging) {
      this.trackPointer(event);
    }
  }

  protected onPointerUp(event: PointerEvent): void {
    if (!this.dragging) {
      return;
    }
    this.dragging = false;
    this.trackPointer(event);
    this.confirm();
  }

  protected onPointerCancel(): void {
    this.dragging = false;
  }

  protected onKeydown(event: KeyboardEvent): void {
    const steps: Record<string, number> = {
      ArrowUp: 1,
      ArrowRight: 1,
      ArrowDown: -1,
      ArrowLeft: -1,
      PageUp: 5,
      PageDown: -5
    };
    if (event.key in steps) {
      event.preventDefault();
      this.step(steps[event.key]);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      this.confirm();
    }
  }

  // Moves the current value by `delta`, wrapping around the dial and skipping disabled values. From no value yet, the
  // first step lands on the first allowed one.
  private step(delta: number): void {
    const hours = this.view() === "hours";
    const count = hours ? 24 : 60;
    const disabled = (value: number) => (hours ? this.isHourDisabled(value) : this.isMinuteDisabled(value));
    const current = this.value();
    let next = current === null ? (delta > 0 ? 0 : count - 1) : (((current + delta) % count) + count) % count;
    const direction = Math.sign(delta);
    for (let tries = 0; disabled(next) && tries < count; tries++) {
      next = (next + direction + count) % count;
    }
    if (disabled(next)) {
      return;
    }
    if (hours) {
      this.setHour(next);
    } else {
      this.minute.set(next);
    }
  }

  // Ends the current step: a chosen hour moves on to the minutes, a chosen minute emits the time.
  private confirm(): void {
    const hour = this.hour();
    if (this.view() === "hours") {
      this.showMinutes();
      return;
    }
    const minute = this.minute();
    if (hour !== null && minute !== null) {
      this.selected.emit({ hour, minute });
    }
  }

  // The value under the pointer becomes the current one, unless it is disabled: then the last allowed one stays.
  private trackPointer(event: PointerEvent): void {
    const rect = this.face().nativeElement.getBoundingClientRect();
    if (!rect.width || !rect.height) {
      return;
    }
    const x = ((event.clientX - rect.left) * CLOCK_DIAL_SIZE) / rect.width;
    const y = ((event.clientY - rect.top) * CLOCK_DIAL_SIZE) / rect.height;
    if (this.view() === "hours") {
      const hour = hourAtPoint(x, y);
      if (!this.isHourDisabled(hour)) {
        this.setHour(hour);
      }
    } else {
      const minute = minuteAtPoint(x, y);
      if (!this.isMinuteDisabled(minute)) {
        this.minute.set(minute);
      }
    }
  }

  // A new hour can make the chosen minute fall before the minimum, which is then dropped.
  private setHour(hour: number): void {
    this.hour.set(hour);
    const minute = this.minute();
    if (minute !== null && this.isMinuteDisabled(minute)) {
      this.minute.set(null);
    }
  }
}
