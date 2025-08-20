import { TestBed } from "@angular/core/testing";

import { provideHttpClient } from "@angular/common/http";
import { ApplicationService } from "./application.service";

describe("ApplicationService", () => {
  let applicationService: ApplicationService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()]
    });
    applicationService = TestBed.inject(ApplicationService);
  });

  it("should be created", () => {
    expect(applicationService).toBeTruthy();
  });
});
