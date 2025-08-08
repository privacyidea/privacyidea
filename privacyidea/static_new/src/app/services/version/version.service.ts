import { Injectable, signal, WritableSignal } from '@angular/core';
import { ROUTE_PATHS } from '../../app.routes';

export interface VersioningServiceInterface {
  version: WritableSignal<string>;

  getVersion(): string;

  openDocumentation(page: string): void;
}

@Injectable({
  providedIn: 'root',
})
export class VersioningService implements VersioningServiceInterface {
  version = signal('');

  getVersion(): string {
    return this.version();
  }

  openDocumentation(page: string) {
    const baseUrl = 'https://privacyidea.readthedocs.io/en/'; //TODO translation
    let page_url;
    if (page.startsWith(ROUTE_PATHS.TOKENS_DETAILS)) {
      page_url = 'webui/token_details.html';
    } else if (page.startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS)) {
      page_url = 'webui/container_view.html#container-details';
    } else {
      switch (page) {
        case ROUTE_PATHS.TOKENS_ENROLLMENT:
          page_url = 'webui/token_details.html#enroll-token';
          break;
        case ROUTE_PATHS.TOKENS:
          page_url = 'webui/index.html#tokens';
          break;
        case ROUTE_PATHS.TOKENS_CONTAINERS:
          page_url = 'webui/index.html#containers';
          break;
        case 'tokentypes':
          page_url = 'tokens/tokentypes.html';
          break;
        case ROUTE_PATHS.TOKENS_GET_SERIAL:
          page_url = 'webui/token_details.html#get-serial';
          break;
        case ROUTE_PATHS.TOKENS_APPLICATIONS:
          page_url = 'machines/index.html';
          break;
        case ROUTE_PATHS.TOKENS_CHALLENGES:
          page_url = 'tokens/authentication_modes.html#challenge-mode';
          break;
        case 'containertypes':
          page_url = 'container/container_types.html';
          break;
        case ROUTE_PATHS.TOKENS_CONTAINERS_CREATE:
          page_url = 'webui/container_view.html#container-create';
          break;
        default:
          page_url = 'webui/index.html';
          break;
      }
    }
    const versionUrl = `${baseUrl}v${this.version()}/${page_url}`;
    const fallbackUrl = `${baseUrl}stable/${page_url}`;

    async function checkPage(url: any) {
      try {
        const response = await fetch(url);
        const html = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        return !doc.querySelector(
          'div.document div.documentwrapper div.bodywrapper div.body h1#notfound',
        );
      } catch (error) {
        console.error('Error checking the page:', error);
        return false;
      }
    }

    checkPage(versionUrl).then((found) => {
      if (found) {
        window.open(versionUrl, '_blank');
      } else {
        checkPage(fallbackUrl).then((foundFallback) => {
          if (foundFallback) {
            window.open(fallbackUrl, '_blank');
          } else {
            alert('The documentation page is currently not available.');
          }
        });
      }
    });
  }
}
