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
import { signal } from "@angular/core";
import { DEBOUNCE_MS, Debouncer } from "./debounce.utils";

describe("Debouncer", () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it("shows the target value while nothing is pending", () => {
    const target = signal("initial");
    const debouncer = new Debouncer(target);

    expect(debouncer.draft()).toBe("initial");

    target.set("changed elsewhere");
    expect(debouncer.draft()).toBe("changed elsewhere");
  });

  describe("schedule", () => {
    it("shows the scheduled value at once but writes it only after the delay", () => {
      const target = signal("initial");
      const debouncer = new Debouncer(target);

      debouncer.schedule("typed");
      expect(debouncer.draft()).toBe("typed");
      expect(target()).toBe("initial");

      jest.advanceTimersByTime(DEBOUNCE_MS - 1);
      expect(target()).toBe("initial");

      jest.advanceTimersByTime(1);
      expect(target()).toBe("typed");
      expect(debouncer.draft()).toBe("typed");
    });

    it("writes only the last of several scheduled values", () => {
      const target = signal("initial");
      const debouncer = new Debouncer(target);

      debouncer.schedule("t");
      jest.advanceTimersByTime(DEBOUNCE_MS - 50);
      debouncer.schedule("ty");
      jest.advanceTimersByTime(DEBOUNCE_MS - 50);
      debouncer.schedule("typ");
      expect(target()).toBe("initial");

      jest.advanceTimersByTime(DEBOUNCE_MS);
      expect(target()).toBe("typ");
    });

    it("honours a custom delay", () => {
      const target = signal("initial");
      const debouncer = new Debouncer(target, 1000);

      debouncer.schedule("typed");
      jest.advanceTimersByTime(DEBOUNCE_MS);
      expect(target()).toBe("initial");

      jest.advanceTimersByTime(1000 - DEBOUNCE_MS);
      expect(target()).toBe("typed");
    });

    it("discards the typed value when the target changed while waiting", () => {
      const target = signal("initial");
      const debouncer = new Debouncer(target);

      debouncer.schedule("typed");
      target.set("reset by route change");

      jest.advanceTimersByTime(DEBOUNCE_MS);
      expect(target()).toBe("reset by route change");
      expect(debouncer.draft()).toBe("reset by route change");
    });
  });

  describe("set", () => {
    it("writes the value at once", () => {
      const target = signal("initial");
      const debouncer = new Debouncer(target);

      debouncer.set("applied");
      expect(target()).toBe("applied");
      expect(debouncer.draft()).toBe("applied");
    });

    it("supersedes a scheduled value", () => {
      const target = signal("initial");
      const debouncer = new Debouncer(target);

      debouncer.schedule("typed");
      debouncer.set("applied");

      jest.advanceTimersByTime(DEBOUNCE_MS);
      expect(target()).toBe("applied");
    });
  });

  describe("update", () => {
    it("computes the new value from the target when nothing is pending", () => {
      const target = signal("initial");
      const debouncer = new Debouncer(target);

      debouncer.update((current) => `${current}!`);
      expect(target()).toBe("initial!");
    });

    it("computes the new value from the draft, so that typed input is not lost", () => {
      const target = signal("initial");
      const debouncer = new Debouncer(target);

      debouncer.schedule("typed");
      debouncer.update((current) => `${current}!`);

      expect(target()).toBe("typed!");
      jest.advanceTimersByTime(DEBOUNCE_MS);
      expect(target()).toBe("typed!");
    });
  });

  describe("cancel", () => {
    it("drops the scheduled value without writing it", () => {
      const target = signal("initial");
      const debouncer = new Debouncer(target);

      debouncer.schedule("typed");
      debouncer.cancel();

      expect(debouncer.draft()).toBe("initial");
      jest.advanceTimersByTime(DEBOUNCE_MS);
      expect(target()).toBe("initial");
    });

    it("does nothing when there is nothing pending", () => {
      const target = signal("initial");
      const debouncer = new Debouncer(target);

      debouncer.cancel();
      expect(target()).toBe("initial");
      expect(debouncer.draft()).toBe("initial");
    });
  });
});
