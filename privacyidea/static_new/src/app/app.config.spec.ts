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

import { APP_BASE_HREF } from "@angular/common";
import { inject, LOCALE_ID } from "@angular/core";
import { TestBed } from "@angular/core/testing";

const baseHrefFactory = () => {
  const locale = inject(LOCALE_ID);
  return locale === "en" || locale.toLowerCase().startsWith("en-")
    ? "/app/v2/"
    : `/app/v2/${locale}/`;
};

describe("APP_BASE_HREF factory", () => {
  afterEach(() => TestBed.resetTestingModule());

  it("returns /app/v2/ for English", () => {
    TestBed.configureTestingModule({
      providers: [
        { provide: LOCALE_ID, useValue: "en" },
        { provide: APP_BASE_HREF, useFactory: baseHrefFactory }
      ]
    });
    expect(TestBed.inject(APP_BASE_HREF)).toBe("/app/v2/");
  });

  it("returns /app/v2/de/ for German", () => {
    TestBed.configureTestingModule({
      providers: [
        { provide: LOCALE_ID, useValue: "de" },
        { provide: APP_BASE_HREF, useFactory: baseHrefFactory }
      ]
    });
    expect(TestBed.inject(APP_BASE_HREF)).toBe("/app/v2/de/");
  });

  it("returns /app/v2/fr/ for French", () => {
    TestBed.configureTestingModule({
      providers: [
        { provide: LOCALE_ID, useValue: "fr" },
        { provide: APP_BASE_HREF, useFactory: baseHrefFactory }
      ]
    });
    expect(TestBed.inject(APP_BASE_HREF)).toBe("/app/v2/fr/");
  });

  it("returns /app/v2/ for en-US (English region variant)", () => {
    TestBed.configureTestingModule({
      providers: [
        { provide: LOCALE_ID, useValue: "en-US" },
        { provide: APP_BASE_HREF, useFactory: baseHrefFactory }
      ]
    });
    expect(TestBed.inject(APP_BASE_HREF)).toBe("/app/v2/");
  });

  it("returns /app/v2/ for en-GB (English region variant)", () => {
    TestBed.configureTestingModule({
      providers: [
        { provide: LOCALE_ID, useValue: "en-GB" },
        { provide: APP_BASE_HREF, useFactory: baseHrefFactory }
      ]
    });
    expect(TestBed.inject(APP_BASE_HREF)).toBe("/app/v2/");
  });

  it("returns /app/v2/zh-Hant/ for Traditional Chinese", () => {
    TestBed.configureTestingModule({
      providers: [
        { provide: LOCALE_ID, useValue: "zh-Hant" },
        { provide: APP_BASE_HREF, useFactory: baseHrefFactory }
      ]
    });
    expect(TestBed.inject(APP_BASE_HREF)).toBe("/app/v2/zh-Hant/");
  });
});
