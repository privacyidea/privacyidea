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
import { InteractivityChecker, LiveAnnouncer } from "@angular/cdk/a11y";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { axe } from "@testing/axe";
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
  const hourField = (): HTMLInputElement => fixture.nativeElement.querySelector(".clock-dial__field--hour");
  const minuteField = (): HTMLInputElement => fixture.nativeElement.querySelector(".clock-dial__field--minute");
  // Typing into a field: its new text and the input event the browser fires for it.
  const type = (field: HTMLInputElement, text: string): void => {
    field.value = text;
    field.dispatchEvent(new Event("input", { bubbles: true }));
    fixture.detectChanges();
  };
  const fieldKey = (field: HTMLInputElement, name: string): void => {
    field.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true }));
    fixture.detectChanges();
  };
  const markClasses = (text: string) =>
    Array.from(fixture.nativeElement.querySelectorAll(".clock-dial__mark") as NodeListOf<Element>).find(
      (mark) => mark.textContent?.trim() === text
    )?.classList;

  async function create(min: ClockTime | null = null): Promise<void> {
    // jsdom does no layout, so the CDK sees every element as invisible and the focus trap would find nothing to focus.
    jest.spyOn(InteractivityChecker.prototype, "isVisible").mockReturnValue(true);
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
    expect(document.getElementById(face().getAttribute("aria-labelledby") as string)?.textContent?.trim()).toBe("Hour");
    expect(face().getAttribute("aria-valuemax")).toBe("23");
  });

  it("a tap on the inner ring picks that hour and moves on to the minutes", async () => {
    await create();
    tap(90, CLOCK_INNER_RADIUS);

    expect(component.hour()).toBe(15);
    expect(component.view()).toBe("minutes");
    expect(document.getElementById(face().getAttribute("aria-labelledby") as string)?.textContent?.trim()).toBe(
      "Minute"
    );
    expect(fixture.nativeElement.querySelectorAll(".clock-dial__mark").length).toBe(12);
    expect(emitted).toEqual([]);
  });

  it("any single minute can be picked, and picking it emits the time", async () => {
    await create();
    tap(30, CLOCK_OUTER_RADIUS);
    tap(42, CLOCK_OUTER_RADIUS);

    expect(component.minute()).toBe(7);
    expect(emitted).toEqual([{ hour: 1, minute: 7 }]);
    expect(hourField().value).toBe("01");
    expect(minuteField().value).toBe("07");
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

    hourField().click();
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

    it("retyping the hour keeps a minute that the finished hour allows", async () => {
      await create({ hour: 14, minute: 30 });
      type(hourField(), "15");
      type(minuteField(), "20");
      type(hourField(), "1");
      expect(minuteField().value).toBe("20");
      expect(component.minute()).toBe(20);

      type(hourField(), "14");
      expect(component.minute()).toBeNull();
      expect(minuteField().value).toBe("");
    });

    it('shows "From 14:30" and ties it to both fields and the dial', async () => {
      await create({ hour: 14, minute: 30 });
      const hint = fixture.nativeElement.querySelector(".clock-dial__hint") as HTMLElement;
      expect(hint.textContent?.trim()).toBe("From 14:30");
      expect(hourField().getAttribute("aria-describedby")).toContain(hint.id);
      expect(minuteField().getAttribute("aria-describedby")).toContain(hint.id);
      expect(face().getAttribute("aria-describedby")).toContain(hint.id);
    });

    it("shows no minimum hint without a minimum", async () => {
      await create();
      expect(fixture.nativeElement.querySelector(".clock-dial__hint")).toBeNull();
      expect(face().hasAttribute("aria-describedby")).toBe(false);
    });

    it("announces the earliest time when a typed digit falls before the minimum", async () => {
      await create({ hour: 9, minute: 30 });
      const announce = jest.spyOn(TestBed.inject(LiveAnnouncer), "announce").mockResolvedValue();
      type(hourField(), "0");
      type(hourField(), "08");
      expect(announce).toHaveBeenCalledWith("Earliest 09:30");
    });

    it("announces nothing when a typed digit is refused only for being past 23 without a minimum", async () => {
      await create();
      const announce = jest.spyOn(TestBed.inject(LiveAnnouncer), "announce").mockResolvedValue();
      type(hourField(), "2");
      type(hourField(), "25");
      expect(announce).not.toHaveBeenCalled();
    });

    it("dragging over disabled hours keeps the last allowed one", async () => {
      await create({ hour: 9, minute: 0 });
      pointer("pointerdown", 300, CLOCK_OUTER_RADIUS);
      pointer("pointermove", 240, CLOCK_OUTER_RADIUS);
      pointer("pointerup", 240, CLOCK_OUTER_RADIUS);
      expect(component.hour()).toBe(10);
    });
  });

  describe("typing", () => {
    it("the hour field has the focus on open", async () => {
      await create();
      expect(document.activeElement).toBe(hourField());
    });

    it("a typed hour moves on to the minute field, a typed minute and Enter emit the time", async () => {
      await create();
      type(hourField(), "09");
      expect(component.hour()).toBe(9);
      expect(component.view()).toBe("minutes");
      expect(document.activeElement).toBe(minuteField());

      type(minuteField(), "45");
      expect(component.minute()).toBe(45);
      expect(emitted).toEqual([]);
      fieldKey(minuteField(), "Enter");

      expect(emitted).toEqual([{ hour: 9, minute: 45 }]);
    });

    it("refuses a keystroke that would make the hour past 23: 2 then 5 stays 2, 1 then 5 gives 15", async () => {
      await create();
      type(hourField(), "2");
      type(hourField(), "25");
      expect(hourField().value).toBe("2");
      expect(component.hour()).toBe(2);
      expect(hourField().getAttribute("aria-invalid")).not.toBe("true");

      type(hourField(), "");
      type(hourField(), "1");
      type(hourField(), "15");
      expect(hourField().value).toBe("15");
      expect(component.hour()).toBe(15);
    });

    it("refuses a keystroke that would make the minute past 59: 6 then 0 stays 6", async () => {
      await create();
      type(hourField(), "10");
      type(minuteField(), "6");
      type(minuteField(), "60");
      expect(minuteField().value).toBe("6");
      expect(component.minute()).toBe(6);
      fieldKey(minuteField(), "Enter");
      expect(emitted).toEqual([{ hour: 10, minute: 6 }]);
    });

    it("refuses a pasted value that is out of range", async () => {
      await create();
      type(hourField(), "1");
      type(hourField(), "99");
      expect(hourField().value).toBe("1");
      expect(component.hour()).toBe(1);
    });

    it("keeps only digits", async () => {
      await create();
      type(hourField(), "1a");
      expect(hourField().value).toBe("1");
      expect(component.hour()).toBe(1);
    });

    it("refuses a keystroke that would make the time fall before the minimum", async () => {
      await create({ hour: 9, minute: 30 });
      // "0" can still become 09, so it is taken, but as an unfinished hour it sets none yet.
      type(hourField(), "0");
      expect(hourField().value).toBe("0");
      expect(component.hour()).toBeNull();
      type(hourField(), "08");
      expect(hourField().value).toBe("0");
      expect(component.hour()).toBeNull();

      type(hourField(), "09");
      expect(component.hour()).toBe(9);
      // No minute from 1 on (1, 10-19) is at or after 9:30, so "1" is refused right away.
      type(minuteField(), "1");
      expect(minuteField().value).toBe("");
      expect(component.minute()).toBeNull();
      fieldKey(minuteField(), "Enter");
      expect(emitted).toEqual([]);

      type(minuteField(), "3");
      expect(minuteField().value).toBe("3");
      expect(component.minute()).toBeNull();
      type(minuteField(), "30");
      fieldKey(minuteField(), "Enter");
      expect(emitted).toEqual([{ hour: 9, minute: 30 }]);
    });

    it("the fields show what the dial picks, the arrow keys in a field step its value", async () => {
      await create();
      tap(90, CLOCK_OUTER_RADIUS);
      expect(hourField().value).toBe("03");

      fieldKey(hourField(), "ArrowUp");
      expect(component.hour()).toBe(4);
      expect(hourField().value).toBe("04");
      fieldKey(minuteField(), "ArrowDown");
      expect(component.minute()).toBe(59);
      expect(minuteField().value).toBe("59");
    });

    it("the hour and minute fields form a group named by the title", async () => {
      await create();
      const group = fixture.nativeElement.querySelector("[role=group]") as HTMLElement;
      expect(group.contains(hourField())).toBe(true);
      expect(group.contains(minuteField())).toBe(true);
      const title = document.getElementById(group.getAttribute("aria-labelledby") as string);
      expect(title?.textContent).toContain("Start time");
    });

    it("the hour and minute fields have visible labels tied to them", async () => {
      await create();
      const labelFor = (field: HTMLInputElement) =>
        fixture.nativeElement.querySelector(`label[for="${field.id}"]`) as HTMLLabelElement;
      expect(labelFor(hourField()).textContent?.trim()).toBe("Hour");
      expect(labelFor(minuteField()).textContent?.trim()).toBe("Minute");

      const second = TestBed.createComponent(ClockDialComponent);
      second.componentRef.setInput("label", "End time");
      second.detectChanges();
      const labelIds = (root: HTMLElement) => Array.from(root.querySelectorAll("label")).map((label) => label.id);
      expect(labelIds(second.nativeElement)).not.toEqual(labelIds(fixture.nativeElement));
    });

    it("the dial is named by the label of the active field", async () => {
      await create();
      const nameOf = () =>
        document.getElementById(face().getAttribute("aria-labelledby") as string)?.textContent?.trim();
      expect(nameOf()).toBe("Hour");
      expect(face().hasAttribute("aria-label")).toBe(false);

      type(hourField(), "09");
      expect(component.view()).toBe("minutes");
      expect(nameOf()).toBe("Minute");
    });

    it("the check button confirms a typed time and stays disabled until hour and minute are set", async () => {
      await create();
      const button = () => fixture.nativeElement.querySelector("button") as HTMLButtonElement;
      type(hourField(), "13");
      expect(button().disabled).toBe(true);

      type(minuteField(), "30");
      expect(button().disabled).toBe(false);
      expect(button().getAttribute("aria-label")).toBe("Confirm time");
      button().click();
      expect(emitted).toEqual([{ hour: 13, minute: 30 }]);
    });

    // Checked with a time set: without a value the dial's slider has no aria-valuenow, which axe flags (known, open).
    it("passes the axe accessibility checks with a typed time", async () => {
      await create();
      type(hourField(), "09");
      type(minuteField(), "30");
      expect(await axe(fixture.nativeElement)).toHaveNoViolations();
    });

    it("Tab stays inside the clock: past the last element it wraps to the hour field, before the first to the dial", async () => {
      await create();
      const anchors = Array.from(document.querySelectorAll<HTMLElement>(".cdk-focus-trap-anchor"));
      expect(anchors.length).toBe(2);

      anchors[1].focus();
      expect(document.activeElement).toBe(hourField());
      anchors[0].focus();
      expect(document.activeElement).toBe(face());
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

    it("the dial value text names the hour in the hour view and the whole time in the minute view", async () => {
      await create();
      tap(60, CLOCK_INNER_RADIUS);
      hourField().click();
      fixture.detectChanges();
      expect(component.view()).toBe("hours");
      expect(face().getAttribute("aria-valuetext")).toBe("Hour 14");

      key("Enter");
      tap(180, CLOCK_OUTER_RADIUS);
      expect(component.view()).toBe("minutes");
      expect(face().getAttribute("aria-valuetext")).toBe("14:30");
    });

    it("Enter on the dial in the hour view announces the minute step and keeps the focus", async () => {
      await create();
      const announce = jest.spyOn(TestBed.inject(LiveAnnouncer), "announce").mockResolvedValue();
      tap(90, CLOCK_OUTER_RADIUS);
      expect(announce).not.toHaveBeenCalled();

      component.view.set("hours");
      fixture.detectChanges();
      face().focus();
      key("Enter");
      expect(announce).toHaveBeenCalledWith("Pick the minute");
      expect(document.activeElement).toBe(face());
    });

    it("Enter without a value does nothing", async () => {
      await create();
      key("Enter");
      expect(component.view()).toBe("hours");
      expect(emitted).toEqual([]);
    });
  });
});
