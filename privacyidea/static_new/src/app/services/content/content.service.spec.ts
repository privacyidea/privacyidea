import { TestBed } from "@angular/core/testing";

import { ContentService } from "./content.service";
import { provideHttpClient } from "@angular/common/http";

describe("ContentService", () => {
  let contentService: ContentService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()]
    });
    contentService = TestBed.inject(ContentService);
  });

  it("should be created", () => {
    expect(contentService).toBeTruthy();
  });
});
