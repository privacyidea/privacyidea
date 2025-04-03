import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class VersionService {
  private readonly version: string;

  constructor() {
    // TODO get version from an environment variable or API
    this.version = '3.11';
  }

  getVersion(): string {
    return this.version;
  }

  openDocumentation(page: string) {
    const baseUrl = 'https://privacyidea.readthedocs.io/en/'; //TODO translation
    let page_url = 'webui';
    switch (page) {
      case 'token_enrollment':
        page_url = 'webui/token_details.html#enroll-token';
        break;
      case 'token_overview':
        page_url = 'webui/index.html#tokens';
        break;
      case 'container_overview':
        page_url = 'webui/index.html#containers';
        break;
      case 'token_details':
        page_url = 'webui/token_details.html';
        break;
      case 'container_details':
        page_url = 'webui/container_view.html#container-details';
        break;
      case 'tokentypes':
        page_url = 'tokens/tokentypes.html';
        break;
      case 'token_get_serial':
        page_url = 'webui/token_details.html#get-serial';
        break;
      case 'token_applications':
        page_url = 'machines/index.html';
        break;
      case 'token_challenges':
        page_url = 'tokens/authentication_modes.html#challenge-mode';
        break;
      case 'containertypes':
        page_url = 'container/container_types.html';
        break;
      case 'container_create':
        page_url = 'webui/container_view.html#container-create';
    }
    const versionUrl = `${baseUrl}v${this.version}/${page_url}`;
    const fallbackUrl = `${baseUrl}latest/${page_url}`;

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
