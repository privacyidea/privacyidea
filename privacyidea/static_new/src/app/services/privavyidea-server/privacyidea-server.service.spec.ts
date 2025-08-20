import { TestBed } from "@angular/core/testing";

import { PrivacyideaServerService } from "./privacyidea-server.service";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("PrivacyideaServerService", () => {
  let privacyideaServerService: PrivacyideaServerService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    privacyideaServerService = TestBed.inject(PrivacyideaServerService);
  });

  it("should be created", () => {
    expect(privacyideaServerService).toBeTruthy();
  });
});
