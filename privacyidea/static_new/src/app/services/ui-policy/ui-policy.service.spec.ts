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
import { UiPolicyService } from "./ui-policy.service";

describe("UiPolicyService", () => {
  afterEach(() => {
    delete (window as any).appConfig;
    jest.restoreAllMocks();
  });

  it("uses window.appConfig when present", () => {
    (window as any).appConfig = {
      remoteUser: "bob",
      forceRemoteUser: "bob",
      passwordReset: true,
      hsmReady: true,
      customization: "custom",
      realms: "realmA",
      logo: "/logo.png",
      showNode: "node‑1",
      externalLinks: true,
      hasJobQueue: "true",
      loginText: "Hello",
      logoutRedirectUrl: "/bye",
      gdprLink: "/gdpr",
      privacyideaVersionNumber: "1.2.3",
      translationWarning: true
    };

    const uiPolicyService = new UiPolicyService();

    expect(uiPolicyService.remoteUser).toBe("bob");
    expect(uiPolicyService.passwordReset).toBe(true);
    expect(uiPolicyService.hsmReady).toBe(true);
    expect(uiPolicyService.customization).toBe("custom");
    expect(uiPolicyService.realms).toBe("realmA");
    expect(uiPolicyService.logo).toBe("/logo.png");
    expect(uiPolicyService.showNode).toBe("node‑1");
    expect(uiPolicyService.externalLinks).toBe(true);
    expect(uiPolicyService.loginText).toBe("Hello");
    expect(uiPolicyService.logoutRedirectUrl).toBe("/bye");
    expect(uiPolicyService.gdprLink).toBe("/gdpr");
    expect(uiPolicyService.privacyideaVersionNumber).toBe("1.2.3");
    expect(uiPolicyService.translationWarning).toBe(true);
    expect(uiPolicyService.hasJobQueue).toBe(true);
  });

  it("falls back to defaults and warns when appConfig is missing", () => {
    const warn = jest.spyOn(console, "warn").mockImplementation(() => {
    });

    const srv = new UiPolicyService();

    expect(warn).toHaveBeenCalledWith(
      "App configuration not found. Using default values."
    );
    expect(srv.remoteUser).toBe("");
    expect(srv.passwordReset).toBe(false);
    expect(srv.hasJobQueue).toBe(true);
  });
});
