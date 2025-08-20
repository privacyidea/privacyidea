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
