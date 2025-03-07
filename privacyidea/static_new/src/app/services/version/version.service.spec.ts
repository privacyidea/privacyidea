import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { VersionService } from './version.service';

describe('VersionService', () => {
  let service: VersionService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VersionService],
    });
    service = TestBed.inject(VersionService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('openDocumentation()', () => {
    const VALID_HTML = `
      <html lang="en">
        <body>
          <div class="document">
            <div class="documentwrapper">
              <div class="bodywrapper">
                <div class="body">
                  <h1>Documentation found</h1>
                </div>
              </div>
            </div>
          </div>
        </body>
      </html>
    `;

    const NOT_FOUND_HTML = `
      <html lang="en">
        <body>
          <div class="document">
            <div class="documentwrapper">
              <div class="bodywrapper">
                <div class="body">
                  <h1 id="notfound">Page Not Found</h1>
                </div>
              </div>
            </div>
          </div>
        </body>
      </html>
    `;
    function mockFetchWithHTML(html: string) {
      return Promise.resolve({
        text: () => Promise.resolve(html),
      } as Response);
    }

    beforeEach(() => {
      spyOn(window, 'open');
      spyOn(window, 'alert');
    });

    it('opens the version-specific URL if it is found', fakeAsync(() => {
      spyOn(window, 'fetch').and.returnValue(mockFetchWithHTML(VALID_HTML));
      service.openDocumentation('token_enrollment');
      tick();
      const expectedUrl =
        'https://privacyidea.readthedocs.io/en/v3.11/webui/token_details.html#enroll-token';
      expect(window.open).toHaveBeenCalledWith(expectedUrl, '_blank');
      expect(window.alert).not.toHaveBeenCalled();
    }));

    it('opens the fallback (latest) URL if the version-specific page is not found', fakeAsync(() => {
      const fetchSpy = spyOn(window, 'fetch').and.returnValues(
        mockFetchWithHTML(NOT_FOUND_HTML),
        mockFetchWithHTML(VALID_HTML),
      );
      service.openDocumentation('token_enrollment');
      tick();
      const expectedFallbackUrl =
        'https://privacyidea.readthedocs.io/en/latest/webui/token_details.html#enroll-token';
      expect(window.open).toHaveBeenCalledWith(expectedFallbackUrl, '_blank');
      expect(window.alert).not.toHaveBeenCalled();

      expect(fetchSpy).toHaveBeenCalledTimes(2);
    }));

    it('alerts if neither version-specific nor fallback page is found', fakeAsync(() => {
      spyOn(window, 'fetch').and.returnValues(
        mockFetchWithHTML(NOT_FOUND_HTML),
        mockFetchWithHTML(NOT_FOUND_HTML),
      );
      service.openDocumentation('token_enrollment');
      tick();
      expect(window.alert).toHaveBeenCalledWith(
        'The documentation page is currently not available.',
      );
      expect(window.open).not.toHaveBeenCalled();
    }));
  });
});
