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
import { FocusTrap, FocusTrapFactory } from "@angular/cdk/a11y";
import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  ElementRef,
  inject,
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
 * Clock face time picker: first the hour on a two-ring 24h dial, then (automatically) the minute. Type the time into
 * the hour and minute fields (the focus starts in the hour field), tap or drag on the dial, or use the arrow keys
 * (PageUp/PageDown step 5) and Enter. Picking the minute on the dial, or Enter with both fields valid, emits `selected`.
 * Times before `min` are greyed out and cannot be picked or typed, so a caller can rule out an end before a start.
 * The focus is trapped inside while the clock is shown, the caller closes it (Escape) and gives the focus back.
 */
@Component({
  selector: "app-clock-dial",
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./clock-dial.component.html",
  styleUrl: "./clock-dial.component.scss",
  host: {
    role: "dialog",
    "aria-modal": "true",
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
  private readonly hourField = viewChild.required<ElementRef<HTMLInputElement>>("hourField");
  private readonly minuteField = viewChild.required<ElementRef<HTMLInputElement>>("minuteField");
  private dragging = false;
  private focusTrap: FocusTrap | null = null;

  // The text of the hour and minute fields. Typing sets it as typed, a value picked on the dial or by an arrow key
  // writes it padded to two digits. A keystroke or paste that could no longer give an allowed value (past 23 / 59, or
  // before `min` whatever digit follows) is refused, and the field keeps its previous text.
  protected readonly hourDraft = signal<string>("");
  protected readonly minuteDraft = signal<string>("");

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
    const host: HTMLElement = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
    const focusTrapFactory: FocusTrapFactory = inject(FocusTrapFactory);
    afterNextRender(() => {
      this.focusTrap = focusTrapFactory.create(host);
      this.hourField().nativeElement.focus();
    });
    inject(DestroyRef).onDestroy(() => this.focusTrap?.destroy());
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

  protected onHourInput(event: Event): void {
    const text: string | null = this.acceptedText(event, this.hourDraft(), 23, (hour) => this.isHourDisabled(hour));
    if (text === null) {
      return;
    }
    this.hourDraft.set(text);
    this.applyHour(this.valueOf(text, 23, (hour) => this.isHourDisabled(hour)));
    if (text.length === 2) {
      this.view.set("minutes");
      this.minuteField().nativeElement.focus();
    }
  }

  protected onMinuteInput(event: Event): void {
    const text: string | null = this.acceptedText(event, this.minuteDraft(), 59, (minute) =>
      this.isMinuteDisabled(minute)
    );
    if (text === null) {
      return;
    }
    this.minuteDraft.set(text);
    this.minute.set(this.valueOf(text, 59, (minute) => this.isMinuteDisabled(minute)));
  }

  // Arrow keys and PageUp/PageDown in a field step its value as on the dial, Enter emits the typed time once both
  // fields hold a valid value, or moves on to the minute field after a valid hour.
  protected onFieldKeydown(event: KeyboardEvent, part: ClockDialView): void {
    const steps: Record<string, number> = { ArrowUp: 1, ArrowDown: -1, PageUp: 5, PageDown: -5 };
    if (event.key in steps) {
      event.preventDefault();
      this.view.set(part === "minutes" && this.hour() === null ? "hours" : part);
      this.step(steps[event.key]);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const hour = this.hour();
      const minute = this.minute();
      if (hour !== null && minute !== null) {
        this.selected.emit({ hour, minute });
      } else if (hour !== null) {
        this.view.set("minutes");
        this.minuteField().nativeElement.focus();
      }
    }
  }

  // The field's new text, its digits only, when it can still give an allowed value: empty, an allowed value itself, or
  // a first digit that some second one makes allowed. Otherwise null, and the field is set back to `previous` with
  // the caret at its end.
  private acceptedText(
    event: Event,
    previous: string,
    max: number,
    disabled: (value: number) => boolean
  ): string | null {
    const field = event.target as HTMLInputElement;
    const digits: string = field.value.replace(/\D/g, "");
    const allowed = (value: number): boolean => value <= max && !disabled(value);
    const first = Number(digits);
    const ok: boolean =
      digits.length === 0 ||
      (digits.length === 1 && (allowed(first) || Array.from({ length: 10 }, (_, d) => first * 10 + d).some(allowed))) ||
      (digits.length === 2 && allowed(first));
    const text: string = ok ? digits : previous;
    if (field.value !== text) {
      field.value = text;
      field.setSelectionRange(text.length, text.length);
    }
    return ok ? text : null;
  }

  // The value an accepted field text stands for, or null while it is empty or an unfinished first digit.
  private valueOf(text: string, max: number, disabled: (value: number) => boolean): number | null {
    const value = Number(text);
    return text && value <= max && !disabled(value) ? value : null;
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
      this.setMinute(next);
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
        this.setMinute(minute);
      }
    }
  }

  // An hour picked on the dial or by an arrow key, written into the hour field too.
  private setHour(hour: number): void {
    this.hourDraft.set(String(hour).padStart(2, "0"));
    this.applyHour(hour);
  }

  private setMinute(minute: number): void {
    this.minuteDraft.set(String(minute).padStart(2, "0"));
    this.minute.set(minute);
  }

  // A new hour can make the chosen minute fall before the minimum, which is then dropped, from its field too.
  private applyHour(hour: number | null): void {
    this.hour.set(hour);
    const minute = this.minute();
    if (minute !== null && this.isMinuteDisabled(minute)) {
      this.minute.set(null);
      this.minuteDraft.set("");
    }
  }
}
