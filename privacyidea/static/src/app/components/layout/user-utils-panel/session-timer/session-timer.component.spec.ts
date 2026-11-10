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
import { SessionTimerService } from "@services/session-timer/session-timer.service";
import { MockSessionTimerService } from "@testing/mock-services";
import { SessionTimerComponent } from "./session-timer.component";

describe("SessionTimerComponent", () => {
  let component: SessionTimerComponent;
  let fixture: ComponentFixture<SessionTimerComponent>;
  let sessionTimerService: MockSessionTimerService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SessionTimerComponent],
      providers: [{ provide: SessionTimerService, useClass: MockSessionTimerService }]
    }).compileComponents();

    sessionTimerService = TestBed.inject(SessionTimerService) as unknown as MockSessionTimerService;
    fixture = TestBed.createComponent(SessionTimerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("shows the rounded time, not the raw one, in the minute before an hour remains", () => {
    sessionTimerService.remainingTime.set(3_599_000);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent.trim()).toBe("1\u202Fh 00\u202Fmin");
  });

  describe("sessionTimeFormat signal", () => {
    it("format less than 10 min is 'm:ss'", () => {
      sessionTimerService.remainingTime.set(10 * 60 * 1000 - 1000);
      expect(component.sessionTimeFormat()).toBe("m:ss");
    });
    it("format less than an hour is 'm min'", () => {
      sessionTimerService.remainingTime.set(59 * 60 * 1000);
      expect(component.sessionTimeFormat()).toBe("m'\u202Fmin'");
    });
    it("format for times equal or larger than an hour is 'H h mm min'", () => {
      sessionTimerService.remainingTime.set(60 * 60 * 1000);
      expect(component.sessionTimeFormat()).toBe("H'\u202Fh' mm'\u202Fmin'");
    });
  });

  describe("session time over a day", () => {
    it("sessionOverOneDay is false below a day and true at/above a day", () => {
      sessionTimerService.remainingTime.set(24 * 60 * 60 * 1000 - 60_000);
      expect(component.sessionOverOneDay()).toBe(false);

      sessionTimerService.remainingTime.set(24 * 60 * 60 * 1000);
      expect(component.sessionOverOneDay()).toBe(true);
    });

    it("counts the last part-minute before a day as a day, since minutes round up", () => {
      sessionTimerService.remainingTime.set(24 * 60 * 60 * 1000 - 1);
      expect(component.sessionOverOneDay()).toBe(true);
    });

    it("sessionOverOneDay defaults to false when remainingTime is undefined", () => {
      sessionTimerService.remainingTime.set(undefined as unknown as number);
      expect(component.sessionOverOneDay()).toBe(false);
    });

    it("sessionDaysText shows only the days when there are no whole hours", () => {
      sessionTimerService.remainingTime.set(24 * 60 * 60 * 1000);
      expect(component.sessionDaysText()).toBe("1\u202Fd");
    });

    it("sessionDaysText appends whole hours (without minutes) when present", () => {
      // 2 days, 5 hours, 30 minutes -> minutes are dropped.
      sessionTimerService.remainingTime.set((2 * 24 + 5) * 60 * 60 * 1000 + 30 * 60 * 1000);
      expect(component.sessionDaysText()).toBe("2\u202Fd 5\u202Fh");
    });
  });

  describe("session length sitting exactly on a format boundary", () => {
    // A session of exactly one hour resets the countdown onto the hour/minute boundary, so reading
    // the raw value flips the format on the first tick after every reset and back on the next
    // activity, changing the width of the panel each time.
    const HOUR_AND_MINUTES = "H'\u202Fh' mm'\u202Fmin'";

    it("keeps the hour format across the first tick after a reset", () => {
      sessionTimerService.remainingTime.set(3_600_000);
      expect(component.sessionTimeFormat()).toBe(HOUR_AND_MINUTES);

      sessionTimerService.remainingTime.set(3_599_000);
      expect(component.sessionTimeFormat()).toBe(HOUR_AND_MINUTES);

      sessionTimerService.remainingTime.set(3_540_001);
      expect(component.sessionTimeFormat()).toBe(HOUR_AND_MINUTES);
    });

    it("moves to minutes only once a full minute below the hour has passed", () => {
      sessionTimerService.remainingTime.set(3_540_000);
      expect(component.sessionTimeFormat()).toBe("m'\u202Fmin'");
    });

    it("shows seconds only once the countdown is genuinely below ten minutes", () => {
      sessionTimerService.remainingTime.set(600_000);
      expect(component.sessionTimeFormat()).toBe("m'\u202Fmin'");

      sessionTimerService.remainingTime.set(599_999);
      expect(component.sessionTimeFormat()).toBe("m:ss");
    });
  });
});
