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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import {
  CLOCK_DIAL_SIZE,
  CLOCK_INNER_RADIUS,
  CLOCK_OUTER_RADIUS,
  ClockDialComponent,
  ClockTime,
  formatClockTime,
  hourAtPoint,
  minuteAtPoint
} from "./clock-dial.component";

const CENTER = CLOCK_DIAL_SIZE / 2;

// The point on the dial (in its own 0..CLOCK_DIAL_SIZE coordinates) at a clock angle, 0 degrees being 12 o'clock.
function polar(degrees: number, radius: number): { x: number; y: number } {
  const rad = (degrees * Math.PI) / 180;
  return { x: CENTER + radius * Math.sin(rad), y: CENTER - radius * Math.cos(rad) };
}

describe("clock dial geometry", () => {
  it.each`
    degrees | ring       | hour
    ${0}    | ${"outer"} | ${12}
    ${0}    | ${"inner"} | ${0}
    ${30}   | ${"outer"} | ${1}
    ${30}   | ${"inner"} | ${13}
    ${90}   | ${"outer"} | ${3}
    ${90}   | ${"inner"} | ${15}
    ${180}  | ${"outer"} | ${6}
    ${180}  | ${"inner"} | ${18}
    ${270}  | ${"inner"} | ${21}
    ${330}  | ${"outer"} | ${11}
    ${330}  | ${"inner"} | ${23}
    ${352}  | ${"outer"} | ${12}
  `("maps the $ring ring at $degrees degrees to hour $hour", ({ degrees, ring, hour }) => {
    const { x, y } = polar(degrees, ring === "outer" ? CLOCK_OUTER_RADIUS : CLOCK_INNER_RADIUS);
    expect(hourAtPoint(x, y)).toBe(hour);
  });

  it("maps a point beyond the outer ring to the outer hour and one near the centre to the inner hour", () => {
    expect(hourAtPoint(polar(60, CENTER).x, polar(60, CENTER).y)).toBe(2);
    expect(hourAtPoint(polar(60, 10).x, polar(60, 10).y)).toBe(14);
  });

  it.each`
    degrees | minute
    ${0}    | ${0}
    ${6}    | ${1}
    ${42}   | ${7}
    ${90}   | ${15}
    ${180}  | ${30}
    ${354}  | ${59}
    ${358}  | ${0}
  `("maps $degrees degrees to minute $minute on any radius", ({ degrees, minute }) => {
    expect(minuteAtPoint(polar(degrees, CLOCK_OUTER_RADIUS).x, polar(degrees, CLOCK_OUTER_RADIUS).y)).toBe(minute);
    expect(minuteAtPoint(polar(degrees, 30).x, polar(degrees, 30).y)).toBe(minute);
  });

  it("formats a time as HH:mm", () => {
    expect(formatClockTime({ hour: 7, minute: 5 })).toBe("07:05");
    expect(formatClockTime({ hour: 23, minute: 59 })).toBe("23:59");
  });
});

describe("ClockDialComponent", () => {
  let fixture: ComponentFixture<ClockDialComponent>;
  let component: ClockDialComponent;
  let emitted: ClockTime[];

  const face = () => fixture.nativeElement.querySelector("[role=slider]") as HTMLElement;
  const pointer = (type: string, degrees: number, radius: number) => {
    const { x, y } = polar(degrees, radius);
    // jsdom has no PointerEvent: a MouseEvent of the pointer type carries the coordinates the dial reads.
    face().dispatchEvent(new MouseEvent(type, { clientX: x, clientY: y, bubbles: true }));
    fixture.detectChanges();
  };
  // A tap on the dial: press and release at the same spot.
  const tap = (degrees: number, radius: number) => {
    pointer("pointerdown", degrees, radius);
    pointer("pointerup", degrees, radius);
  };
  const key = (name: string) => {
    face().dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true }));
    fixture.detectChanges();
  };
  const markClasses = (text: string) =>
    Array.from(fixture.nativeElement.querySelectorAll(".clock-dial__mark") as NodeListOf<Element>).find(
      (mark) => mark.textContent?.trim() === text
    )?.classList;

  async function create(min: ClockTime | null = null): Promise<void> {
    await TestBed.configureTestingModule({ imports: [ClockDialComponent] }).compileComponents();
    fixture = TestBed.createComponent(ClockDialComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput("label", "Start time");
    fixture.componentRef.setInput("min", min);
    emitted = [];
    component.selected.subscribe((time) => emitted.push(time));
    fixture.detectChanges();
    // jsdom does no layout: the dial is drawn at its natural size at the viewport origin.
    jest.spyOn(face(), "getBoundingClientRect").mockReturnValue({
      left: 0,
      top: 0,
      width: CLOCK_DIAL_SIZE,
      height: CLOCK_DIAL_SIZE,
      right: CLOCK_DIAL_SIZE,
      bottom: CLOCK_DIAL_SIZE,
      x: 0,
      y: 0,
      toJSON: () => ({})
    });
  }

  afterEach(() => TestBed.resetTestingModule());

  it("starts on the hours with both rings labelled and no value", async () => {
    await create();
    expect(component.view()).toBe("hours");
    expect(fixture.nativeElement.querySelectorAll(".clock-dial__mark").length).toBe(24);
    expect(markClasses("12")?.contains("clock-dial__mark--inner")).toBe(false);
    expect(markClasses("00")?.contains("clock-dial__mark--inner")).toBe(true);
    expect(markClasses("13")?.contains("clock-dial__mark--inner")).toBe(true);
    expect(fixture.nativeElement.querySelector(".clock-dial__title").textContent).toContain("Start time");
    expect(face().getAttribute("aria-label")).toBe("Hour");
    expect(face().getAttribute("aria-valuemax")).toBe("23");
  });

  it("a tap on the inner ring picks that hour and moves on to the minutes", async () => {
    await create();
    tap(90, CLOCK_INNER_RADIUS);

    expect(component.hour()).toBe(15);
    expect(component.view()).toBe("minutes");
    expect(face().getAttribute("aria-label")).toBe("Minute");
    expect(fixture.nativeElement.querySelectorAll(".clock-dial__mark").length).toBe(12);
    expect(emitted).toEqual([]);
  });

  it("any single minute can be picked, and picking it emits the time", async () => {
    await create();
    tap(30, CLOCK_OUTER_RADIUS);
    tap(42, CLOCK_OUTER_RADIUS);

    expect(component.minute()).toBe(7);
    expect(emitted).toEqual([{ hour: 1, minute: 7 }]);
    expect(fixture.nativeElement.querySelector(".clock-dial__readout").textContent).toContain("01");
    expect(fixture.nativeElement.querySelector(".clock-dial__readout").textContent).toContain("07");
  });

  it("dragging follows the pointer and commits where it is released", async () => {
    await create();
    pointer("pointerdown", 30, CLOCK_OUTER_RADIUS);
    pointer("pointermove", 60, CLOCK_OUTER_RADIUS);
    expect(component.hour()).toBe(2);
    expect(component.view()).toBe("hours");
    pointer("pointermove", 120, CLOCK_INNER_RADIUS);
    pointer("pointerup", 120, CLOCK_INNER_RADIUS);

    expect(component.hour()).toBe(16);
    expect(component.view()).toBe("minutes");

    pointer("pointerdown", 0, CLOCK_OUTER_RADIUS);
    pointer("pointermove", 180, CLOCK_OUTER_RADIUS);
    pointer("pointerup", 186, CLOCK_OUTER_RADIUS);
    expect(emitted).toEqual([{ hour: 16, minute: 31 }]);
  });

  it("a pointer move without a press changes nothing", async () => {
    await create();
    pointer("pointermove", 90, CLOCK_OUTER_RADIUS);
    expect(component.hour()).toBeNull();
  });

  it("the hour in the readout switches back to the hours", async () => {
    await create();
    tap(90, CLOCK_OUTER_RADIUS);
    expect(component.view()).toBe("minutes");

    (fixture.nativeElement.querySelector(".clock-dial__part") as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(component.view()).toBe("hours");
    expect(component.hour()).toBe(3);
  });

  describe("with a minimum time", () => {
    it("disables the hours before it, and those cannot be picked", async () => {
      await create({ hour: 9, minute: 30 });

      expect(markClasses("8")?.contains("clock-dial__mark--disabled")).toBe(true);
      expect(markClasses("00")?.contains("clock-dial__mark--disabled")).toBe(true);
      expect(markClasses("9")?.contains("clock-dial__mark--disabled")).toBe(false);
      expect(markClasses("23")?.contains("clock-dial__mark--disabled")).toBe(false);
      expect(component.isHourDisabled(8)).toBe(true);
      expect(component.isHourDisabled(9)).toBe(false);

      tap(240, CLOCK_OUTER_RADIUS);
      expect(component.hour()).toBeNull();
      expect(component.view()).toBe("hours");
    });

    it("in the minimum hour disables the minutes before it, in a later hour none", async () => {
      await create({ hour: 9, minute: 30 });
      tap(270, CLOCK_OUTER_RADIUS);
      expect(component.hour()).toBe(9);

      expect(markClasses("15")?.contains("clock-dial__mark--disabled")).toBe(true);
      expect(markClasses("30")?.contains("clock-dial__mark--disabled")).toBe(false);
      tap(90, CLOCK_OUTER_RADIUS);
      expect(emitted).toEqual([]);
      expect(component.minute()).toBeNull();

      tap(180, CLOCK_OUTER_RADIUS);
      expect(emitted).toEqual([{ hour: 9, minute: 30 }]);

      component.view.set("hours");
      fixture.detectChanges();
      tap(300, CLOCK_OUTER_RADIUS);
      expect(component.hour()).toBe(10);
      expect(markClasses("00")?.contains("clock-dial__mark--disabled")).toBe(false);
      expect(component.isMinuteDisabled(0)).toBe(false);
    });

    it("dragging over disabled hours keeps the last allowed one", async () => {
      await create({ hour: 9, minute: 0 });
      pointer("pointerdown", 300, CLOCK_OUTER_RADIUS);
      pointer("pointermove", 240, CLOCK_OUTER_RADIUS);
      pointer("pointerup", 240, CLOCK_OUTER_RADIUS);
      expect(component.hour()).toBe(10);
    });
  });

  describe("keyboard", () => {
    it("arrows step through the allowed values, Enter confirms the hour and then the minute", async () => {
      await create({ hour: 9, minute: 30 });
      face().focus();

      key("ArrowUp");
      expect(component.hour()).toBe(9);
      expect(face().getAttribute("aria-valuenow")).toBe("9");
      key("ArrowDown");
      expect(component.hour()).toBe(23);
      key("ArrowRight");
      expect(component.hour()).toBe(9);
      key("Enter");
      expect(component.view()).toBe("minutes");

      key("ArrowUp");
      expect(component.minute()).toBe(30);
      key("ArrowUp");
      expect(component.minute()).toBe(31);
      key("ArrowLeft");
      key("ArrowDown");
      expect(component.minute()).toBe(59);
      key("PageDown");
      expect(component.minute()).toBe(54);
      expect(emitted).toEqual([]);

      key("Enter");
      expect(emitted).toEqual([{ hour: 9, minute: 54 }]);
    });

    it("Enter without a value does nothing", async () => {
      await create();
      key("Enter");
      expect(component.view()).toBe("hours");
      expect(emitted).toEqual([]);
    });
  });
});
