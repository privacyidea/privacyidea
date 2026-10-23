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
import { downloadBlob, OBJECT_URL_LIFETIME_MS } from "./download.utils";

describe("downloadBlob", () => {
  let clickedAnchors: HTMLAnchorElement[];
  let revokedUrls: string[];
  const originalCreateObjectURL = window.URL.createObjectURL;
  const originalRevokeObjectURL = window.URL.revokeObjectURL;

  beforeEach(() => {
    jest.useFakeTimers();
    // jsdom neither creates object URLs nor follows links, the URLs and links are recorded instead
    clickedAnchors = [];
    revokedUrls = [];
    window.URL.createObjectURL = jest.fn(() => "blob:download");
    window.URL.revokeObjectURL = jest.fn((url: string) => revokedUrls.push(url));
    jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clickedAnchors.push(this);
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
    window.URL.createObjectURL = originalCreateObjectURL;
    window.URL.revokeObjectURL = originalRevokeObjectURL;
  });

  it("clicks a link that saves the blob under the file name", () => {
    const blob = new Blob(["content"], { type: "text/plain" });

    downloadBlob(blob, "file.txt");

    expect(window.URL.createObjectURL).toHaveBeenCalledWith(blob);
    expect(clickedAnchors).toHaveLength(1);
    expect(clickedAnchors[0].getAttribute("href")).toBe("blob:download");
    expect(clickedAnchors[0].download).toBe("file.txt");
  });

  it("releases the object URL only after the browser had time to read the file", () => {
    downloadBlob(new Blob(["content"]), "file.txt");

    jest.advanceTimersByTime(OBJECT_URL_LIFETIME_MS - 1);
    expect(revokedUrls).toEqual([]);

    jest.advanceTimersByTime(1);
    expect(revokedUrls).toEqual(["blob:download"]);
  });
});
