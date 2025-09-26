/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { TestBed } from "@angular/core/testing";
import { VersioningService } from "./version.service";

const VALID_HTML = `
  <html><body>
    <div class="document"><div class="documentwrapper">
      <div class="bodywrapper"><div class="body">
        <h1>Documentation found</h1>
      </div></div>
    </div></div>
  </body></html>
`;

const NOT_FOUND_HTML = `
  <html><body>
    <div class="document"><div class="documentwrapper">
      <div class="bodywrapper"><div class="body">
        <h1 id="notfound">Page Not Found</h1>
      </div></div>
    </div></div>
  </body></html>
`;

const mockFetchWithHTML = (html: string): Promise<Response> =>
  Promise.resolve({
    text: () => Promise.resolve(html)
  } as unknown as Response);

const flushPromises = () => new Promise((r) => setTimeout(r, 0));

describe("versioningService", () => {
  let versioningService: VersioningService;

  beforeAll(() => {
    if (!(global as any).fetch) {
      (global as any).fetch = jest.fn();
    }
  });

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [VersioningService] });
    versioningService = TestBed.inject(VersioningService);

    jest.spyOn(console, "error").mockImplementation(() => {
    });
    jest.spyOn(window, "open").mockImplementation(jest.fn());
    jest.spyOn(window, "alert").mockImplementation(jest.fn());
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("should be created", () => {
    expect(versioningService).toBeTruthy();
  });

  describe("openDocumentation()", () => {
    it("opens the version-specific URL when the page exists", async () => {
      versioningService.version.set("3.12");

      jest.spyOn(global, "fetch").mockImplementation(() => mockFetchWithHTML(VALID_HTML));

      versioningService.openDocumentation("/tokens/enrollment");
      await flushPromises();

      const expectedUrl =
        "https://privacyidea.readthedocs.io/en/v3.12/webui/token_details.html#enroll-token";

      expect(window.open).toHaveBeenCalledWith(expectedUrl, "_blank");
      expect(window.alert).not.toHaveBeenCalled();
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it("falls back to the latest URL when the version page is missing", async () => {
      versioningService.version.set("3.12");

      jest
        .spyOn(global, "fetch")
        .mockImplementationOnce(() => mockFetchWithHTML(NOT_FOUND_HTML))
        .mockImplementationOnce(() => mockFetchWithHTML(VALID_HTML));

      versioningService.openDocumentation("/tokens/enrollment");
      await flushPromises();
      await flushPromises();

      const fallbackUrl =
        "https://privacyidea.readthedocs.io/en/stable/webui/token_details.html#enroll-token";

      expect(window.open).toHaveBeenCalledWith(fallbackUrl, "_blank");
      expect(window.alert).not.toHaveBeenCalled();
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it("shows an alert if neither page exists", async () => {
      versioningService.version.set("3.12");

      jest.spyOn(global, "fetch").mockImplementation(() => mockFetchWithHTML(NOT_FOUND_HTML));

      versioningService.openDocumentation("/tokens/enroll");
      await flushPromises();
      await flushPromises();

      expect(window.alert).toHaveBeenCalledWith(
        "The documentation page is currently not available."
      );
      expect(window.open).not.toHaveBeenCalled();
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  describe("openDocumentation() – more cases", () => {
    const mockRejectedFetch = (msg = "network"): Promise<Response> =>
      Promise.reject(new Error(msg)) as any;

    beforeEach(() => {
      (window.open as jest.Mock).mockClear();
      (window.alert as jest.Mock).mockClear();
      (global.fetch as jest.Mock).mockReset();
    });

    it("falls back to latest when the version page request rejects (network error)", async () => {
      versioningService.version.set("3.12");

      (global.fetch as jest.Mock)
        .mockImplementationOnce(() => mockRejectedFetch("net-err"))
        .mockImplementationOnce(() => mockFetchWithHTML(VALID_HTML));

      versioningService.openDocumentation("/tokens/enrollment");

      await flushPromises();
      await flushPromises();

      const fallbackUrl =
        "https://privacyidea.readthedocs.io/en/stable/webui/token_details.html#enroll-token";

      expect(window.open).toHaveBeenCalledWith(fallbackUrl, "_blank");
      expect(window.alert).not.toHaveBeenCalled();
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it("shows an alert when both versioned and latest checks reject (network errors)", async () => {
      versioningService.version.set("3.12");

      (global.fetch as jest.Mock)
        .mockImplementationOnce(() => mockRejectedFetch("v-fail"))
        .mockImplementationOnce(() => mockRejectedFetch("stable-fail"));

      versioningService.openDocumentation("/tokens/enrollment");

      await flushPromises();
      await flushPromises();

      expect(window.alert).toHaveBeenCalledWith("The documentation page is currently not available.");
      expect(window.open).not.toHaveBeenCalled();
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it("normalizes patch versions (e.g., 3.12.4) when building the docs URL", async () => {
      versioningService.version.set("3.12.4");

      (global.fetch as jest.Mock).mockImplementation(() => mockFetchWithHTML(VALID_HTML));

      versioningService.openDocumentation("/tokens/enrollment");
      await flushPromises();

      const openedUrl = (window.open as jest.Mock).mock.calls[0][0] as string;
      expect(openedUrl).toBe(
        "https://privacyidea.readthedocs.io/en/v3.12.4/webui/token_details.html#enroll-token"
      );
      expect(openedUrl).toContain("webui/token_details.html#enroll-token");
      expect(window.alert).not.toHaveBeenCalled();
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });
  });
});
