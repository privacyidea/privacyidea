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

import { TimeRangeSlider } from "./time-range-slider";

describe("TimeRangeSlider", () => {
  let fixture: ComponentFixture<TimeRangeSlider>;
  let element: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [TimeRangeSlider] }).compileComponents();
    fixture = TestBed.createComponent(TimeRangeSlider);
    fixture.componentRef.setInput("histogram", [0.25, 1, 0.5]);
    fixture.componentRef.setInput("steps", 200);
    fixture.componentRef.setInput("start", 20);
    fixture.componentRef.setInput("end", 180);
    fixture.componentRef.setInput("summaryFrom", "Jun 1, 2026");
    fixture.componentRef.setInput("summaryTo", "Jun 5, 2026");
    // Names a position the way the summaries do, as the log's own formatter does: Material writes the accessible value
    // from it too, so the two must agree.
    fixture.componentRef.setInput("displayWith", (pos: number) => (pos <= 20 ? "Jun 1, 2026" : "Jun 5, 2026"));
    fixture.detectChanges();
    element = fixture.nativeElement;
  });

  it("draws one bar per histogram bin at its share of the height", () => {
    const heights = Array.from(element.querySelectorAll<HTMLElement>(".activity-bar")).map((bar) => bar.style.height);
    expect(heights).toEqual(["25%", "100%", "50%"]);
  });

  it("shows the range summary", () => {
    const summary = Array.from(element.querySelectorAll(".range-summary span")).map((span) => span.textContent?.trim());
    expect(summary).toEqual(["Jun 1, 2026", "Jun 5, 2026"]);
  });

  it("places the thumbs at the given positions", () => {
    const [start, end] = Array.from(element.querySelectorAll<HTMLInputElement>("input"));
    expect(start.value).toBe("20");
    expect(end.value).toBe("180");
  });

  it("reports a thumb's position while it is dragged", () => {
    const startInput = jest.fn();
    fixture.componentInstance.startInput.subscribe(startInput);
    const start = element.querySelector<HTMLInputElement>("input")!;
    start.value = "50";
    start.dispatchEvent(new Event("input"));
    expect(startInput).toHaveBeenCalledWith(50);
  });

  it("gives each thumb its summary as the accessible value", () => {
    const [start, end] = Array.from(element.querySelectorAll<HTMLInputElement>("input"));
    expect(start.getAttribute("aria-valuetext")).toBe("Jun 1, 2026");
    expect(end.getAttribute("aria-valuetext")).toBe("Jun 5, 2026");
  });

  it("reports a released thumb as a commit", () => {
    const commit = jest.fn();
    fixture.componentInstance.commit.subscribe(commit);
    element.querySelector("input")!.dispatchEvent(new Event("change"));
    expect(commit).toHaveBeenCalledTimes(1);
  });
});
