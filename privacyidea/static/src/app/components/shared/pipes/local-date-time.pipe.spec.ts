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

import * as dateFormatUtils from "@utils/date-format.utils";
import { LocalDateTimePipe } from "./local-date-time.pipe";

// Exact formatting correctness is covered by date-format.utils.spec.ts; this pipe is only
// wiring, so it's verified against a mock rather than duplicating the format expectations.
jest.mock("@utils/date-format.utils");

describe("LocalDateTimePipe", () => {
  const pipe = new LocalDateTimePipe();

  afterEach(() => {
    jest.resetAllMocks();
  });

  it("delegates the value to formatLocalDateTime and returns its result", () => {
    jest.spyOn(dateFormatUtils, "formatLocalDateTime").mockReturnValue("Jul 1, 2026, 10:30:45 AM");

    const result = pipe.transform("2026-07-01T10:30:45Z");

    expect(dateFormatUtils.formatLocalDateTime).toHaveBeenCalledWith("2026-07-01T10:30:45Z");
    expect(result).toBe("Jul 1, 2026, 10:30:45 AM");
  });

  it("passes null/undefined/empty input through unmodified", () => {
    jest.spyOn(dateFormatUtils, "formatLocalDateTime").mockReturnValue("");

    pipe.transform(null);
    expect(dateFormatUtils.formatLocalDateTime).toHaveBeenCalledWith(null);

    pipe.transform(undefined);
    expect(dateFormatUtils.formatLocalDateTime).toHaveBeenCalledWith(undefined);

    pipe.transform("");
    expect(dateFormatUtils.formatLocalDateTime).toHaveBeenCalledWith("");
  });
});
