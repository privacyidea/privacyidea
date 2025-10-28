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
import { inject, Injectable, signal, WritableSignal } from "@angular/core";
import { ROUTE_PATHS } from "../../route_paths";
import { VersioningService } from "../version/version.service";

export interface DocumentationServiceInterface {}

@Injectable({
  providedIn: "root"
})
export class DocumentationService implements DocumentationServiceInterface {
  private _versioningService = inject(VersioningService);
  private _version = this._versioningService.version;
  private _baseUrl = "https://privacyidea.readthedocs.io/en/"; //TODO translation

  getVersionUrl(pageUrl: string): string {
    pageUrl = pageUrl.replace(/^\/+/, ""); // Remove leading slashes
    return `${this._baseUrl}v${this._version()}/${pageUrl}`;
  }
  getFallbackUrl(pageUrl: string): string {
    pageUrl = pageUrl.replace(/^\/+/, ""); // Remove leading slashes
    return `${this._baseUrl}stable/${pageUrl}`;
  }

  openDocumentation(page: string) {
    let pageUrl;
    if (page.startsWith(ROUTE_PATHS.TOKENS_DETAILS)) {
      pageUrl = "webui/token_details.html";
    } else if (page.startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS)) {
      pageUrl = "webui/container_view.html#container-details";
    } else {
      switch (page) {
        case ROUTE_PATHS.TOKENS_ENROLLMENT:
          pageUrl = "webui/token_details.html#enroll-token";
          break;
        case ROUTE_PATHS.TOKENS:
          pageUrl = "webui/index.html#tokens";
          break;
        case ROUTE_PATHS.TOKENS_CONTAINERS:
          pageUrl = "webui/index.html#containers";
          break;
        case "tokentypes":
          pageUrl = "tokens/tokentypes.html";
          break;
        case ROUTE_PATHS.TOKENS_GET_SERIAL:
          pageUrl = "webui/token_details.html#get-serial";
          break;
        case ROUTE_PATHS.TOKENS_APPLICATIONS:
          pageUrl = "machines/index.html";
          break;
        case ROUTE_PATHS.TOKENS_CHALLENGES:
          pageUrl = "tokens/authentication_modes.html#challenge-mode";
          break;
        case "containertypes":
          pageUrl = "container/container_types.html";
          break;
        case ROUTE_PATHS.TOKENS_CONTAINERS_CREATE:
          pageUrl = "webui/container_view.html#container-create";
          break;
        default:
          pageUrl = "webui/index.html";
          break;
      }
    }
    const versionUrl = this.getVersionUrl(pageUrl);
    const fallbackUrl = this.getFallbackUrl(pageUrl);

    this.checkFullUrl(versionUrl).then((found) => {
      if (found) {
        window.open(versionUrl, "_blank");
      } else {
        this.checkFullUrl(fallbackUrl).then((foundFallback) => {
          if (foundFallback) {
            window.open(fallbackUrl, "_blank");
          } else {
            alert("The documentation page is currently not available.");
          }
        });
      }
    });
  }

  /**
   * * @param url The full URL to check (including base URL and page URL)
   * * Checks if the documentation page exists by fetching and parsing the HTML content.
   * * @returns A promise that resolves to true if the page exists, false otherwise.
   */

  async checkFullUrl(url: string): Promise<boolean> {
    try {
      const response = await fetch(url);
      const html = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");
      return !doc.querySelector("div.document div.documentwrapper div.bodywrapper div.body h1#notfound");
    } catch (error) {
      console.error("Error checking the page:", error);
      return false;
    }
  }

  /**
   *
   * @param pageUrl The page URL to check (relative to the documentation base URL)
   *  * Checks if the documentation page exists for the current version or falls back to stable.
   *  * Alerts the user if the page is not found in either version.
   *
   * @returns A promise that resolves to the found URL or false if not found.
   */
  async checkPageUrl(pageUrl: string): Promise<string | false> {
    const versionUrl = this.getVersionUrl(pageUrl);

    return this.checkFullUrl(versionUrl).then((found) => {
      if (found) {
        return versionUrl;
      } else {
        const fallbackUrl = this.getFallbackUrl(pageUrl);
        return this.checkFullUrl(fallbackUrl).then((foundFallback) => {
          if (foundFallback) {
            return fallbackUrl;
          } else {
            alert("The documentation page is currently not available.");
            return false;
          }
        });
      }
    });
  }

  openDocumentationPage(page: string): Promise<boolean> {
    // First check the page and when found open it
    return new Promise((_) => {
      const versionUrl = this.getVersionUrl(page);
      this.checkFullUrl(versionUrl).then((found) => {
        if (found) {
          window.open(versionUrl, "_blank");
        } else {
          const fallbackUrl = this.getFallbackUrl(page);
          this.checkFullUrl(fallbackUrl).then((foundFallback) => {
            if (foundFallback) {
              window.open(fallbackUrl, "_blank");
            } else {
              alert("The documentation page is currently not available.");
            }
          });
        }
      });
    });
  }
  async getPoliciesDocumentation(
    scope: string,
    sectionId: string
  ): Promise<{ baseParts: string[]; noteParts: string[] } | null> {
    const pageUrl = "policies/" + scope + ".html";
    const existingPage = await this.checkPageUrl(pageUrl);
    if (!existingPage) return null;
    const response = await fetch(existingPage);
    const html = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");

    const section = doc.getElementById(sectionId);

    const baseParts: string[] = [];
    const noteParts: string[] = [];

    if (!section) {
      return null;
    }
    section.childNodes.forEach((node) => {
      if (node.nodeType === Node.ELEMENT_NODE) {
        const element = node as HTMLElement;
        if (element.tagName.toLowerCase() === "p") {
          // Exclude type paragraphs
          if (!element.textContent?.startsWith("type:")) {
            baseParts.push(element.outerHTML);
          }
        } else if (
          element.tagName.toLowerCase() === "div" &&
          element.classList.contains("admonition") &&
          element.classList.contains("note")
        ) {
          noteParts.push(element.outerHTML);
        }
      }
    });
    return { baseParts, noteParts };
  }
}
