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
import { DocumentationService } from "./documentation.service";
import { VersioningService } from "../version/version.service";
import { PolicyService } from "../policies/policies.service";
import { signal } from "@angular/core";

class MockVersioningService {
  version = signal("3.9.1+123.456");
}

class MockPolicyService {
  selectedAction = signal<{ name: string } | null>(null);
  selectedPolicyScope = signal<string | null>(null);
}

describe("DocumentationService", () => {
  let service: DocumentationService;
  let versioningService: MockVersioningService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        DocumentationService,
        { provide: VersioningService, useClass: MockVersioningService },
        { provide: PolicyService, useClass: MockPolicyService },
      ],
    });
    service = TestBed.inject(DocumentationService);
    versioningService = TestBed.inject(VersioningService) as any;
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("getVersionUrl should construct the correct versioned URL", () => {
    const url = service.getVersionUrl("some/page.html");
    expect(url).toBe("https://privacyidea.readthedocs.io/en/v3.9.1/some/page.html");
  });

  it("getFallbackUrl should construct the correct stable URL", () => {
    const url = service.getFallbackUrl("some/page.html");
    expect(url).toBe("https://privacyidea.readthedocs.io/en/stable/some/page.html");
  });

  describe("openDocumentation", () => {
    let windowOpenSpy: jest.SpyInstance;
    let checkFullUrlSpy: jest.SpyInstance;

    beforeEach(() => {
      windowOpenSpy = jest.spyOn(window, "open").mockImplementation(() => null);
      checkFullUrlSpy = jest.spyOn(service, "checkFullUrl");
    });

    afterEach(() => {
      windowOpenSpy.mockRestore();
      checkFullUrlSpy.mockRestore();
    });

    it("should open versioned URL if it exists", async () => {
      checkFullUrlSpy.mockResolvedValue(true);
      await service.openDocumentation("tokens");
      expect(checkFullUrlSpy).toHaveBeenCalledWith("https://privacyidea.readthedocs.io/en/v3.9.1/webui/index.html#tokens");
      expect(windowOpenSpy).toHaveBeenCalledWith("https://privacyidea.readthedocs.io/en/v3.9.1/webui/index.html#tokens", "_blank");
    });

    it("should open fallback URL if versioned URL does not exist", async () => {
      checkFullUrlSpy.mockImplementation(async (url: string) => {
        return url.includes("stable");
      });
      await service.openDocumentation("tokens");
      expect(checkFullUrlSpy).toHaveBeenCalledWith("https://privacyidea.readthedocs.io/en/v3.9.1/webui/index.html#tokens");
      expect(checkFullUrlSpy).toHaveBeenCalledWith("https://privacyidea.readthedocs.io/en/stable/webui/index.html#tokens");
      expect(windowOpenSpy).toHaveBeenCalledWith("https://privacyidea.readthedocs.io/en/stable/webui/index.html#tokens", "_blank");
    });

    it("should show alert if no documentation is found", async () => {
      const alertSpy = jest.spyOn(window, "alert").mockImplementation(() => {});
      checkFullUrlSpy.mockResolvedValue(false);
      await service.openDocumentation("tokens");
      expect(alertSpy).toHaveBeenCalledWith("The documentation page is currently not available.");
      alertSpy.mockRestore();
    });
  });
});
