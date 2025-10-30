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
import { computed, effect, inject, Injectable, linkedSignal, signal, WritableSignal } from "@angular/core";
import { ROUTE_PATHS } from "../../route_paths";
import { VersioningService } from "../version/version.service";
import { version } from "uuid";
import { httpResource } from "@angular/common/http";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { PolicyService } from "../policies/policies.service";

export interface DocumentationServiceInterface {
  openDocumentation(page: string): void;
  getVersionUrl(pageUrl: string): string;
  getFallbackUrl(pageUrl: string): string;
  checkFullUrl(url: string): Promise<boolean>;
  checkPageUrl(pageUrl: string): Promise<string | false>;
  openDocumentationPage(page: string): Promise<boolean>;
  getPolicyActionDocumentation(
    scope: string,
    sectionId: string
  ): Promise<{ actionDocu: string[]; actionNotes: string[] } | null>;
}

@Injectable({
  providedIn: "root"
})
export class DocumentationService {
  private _versioningService = inject(VersioningService);
  private _policyActionService: PolicyService = inject(PolicyService);
  private _version = this._versioningService.version;
  private _baseUrl = "https://privacyidea.readthedocs.io/en/"; //TODO translation

  getVersionUrl(pageUrl: string): string {
    pageUrl = pageUrl.replace(/^\/+/, ""); // Remove leading slashes
    const version = this._version().split("+")[0];
    return `${this._baseUrl}v${version}/${pageUrl}`;
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

  checkResponseFound(response: Response): boolean {
    return response.ok; // Temporary simple check replace later with full HTML parsing
    // const html = await response.text();
    // const parser = new DOMParser();
    // const doc = parser.parseFromString(html, "text/html");
    // return !doc.querySelector("div.document div.documentwrapper div.bodywrapper div.body h1#notfound");
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

  policyActionSectionId = computed<string | null>(() => {
    const selectedAction = this._policyActionService.selectedAction()?.name;
    console.log("policyActionSectionId selectedAction:", selectedAction);
    if (!selectedAction) return null;
    return selectedAction.replaceAll("_", "-").toLowerCase();
  });

  policyActionDocumentationResource = httpResource.text(() => {
    const scope = this._policyActionService.selectedPolicyScope();
    if (!scope) return undefined;
    console.log("policyActionDocumentationResource scope:", scope);
    const page = "policies/" + scope + ".html";
    return {
      url: this.getVersionUrl(page),
      method: "GET",
      responseType: "text"
    };
  });
  policyActionDocumentationFallbackResource = httpResource.text(() => {
    const scope = this._policyActionService.selectedPolicyScope();
    console.log("policyActionDocumentationFallbackResource scope:", scope);
    if (!scope) return undefined;
    const page = "policies/" + scope + ".html";
    return {
      url: this.getFallbackUrl(page),
      method: "GET",
      responseType: "text"
    };
  });

  policyActionDocumentation = computed(() => {
    let html = this.policyActionDocumentationResource.value();

    console.log("resourceType:", typeof html);
    if (!html) {
      html = this.policyActionDocumentationFallbackResource.value();
    }
    if (!html) {
      console.warn("No documentation resource found");
      return null;
    }
    console.log("html:", html);
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    console.log("doc:", doc);
    let sectionId = this.policyActionSectionId();
    if (!sectionId) {
      console.warn("No sectionId found");
      return null;
    }
    console.log("sectionId:", sectionId);

    const section = doc.getElementById(sectionId);

    const actionDocu: string[] = [];
    const actionNotes: string[] = [];

    console.log("section:", section);
    if (!section) {
      return null;
    }
    console.log("Found section:", section);
    section.childNodes.forEach((node) => {
      if (node.nodeType === Node.ELEMENT_NODE) {
        const element = node as HTMLElement;
        console.log("Found element:", element);
        if (element.tagName.toLowerCase() === "p") {
          // Exclude type paragraphs
          if (!element.textContent?.startsWith("type:")) {
            console.log("Adding to actionDocu:", element.outerHTML);
            actionDocu.push(element.outerHTML);
          }
        } else if (
          element.tagName.toLowerCase() === "div" &&
          element.classList.contains("admonition") &&
          element.classList.contains("note")
        ) {
          // remove <p class="admonition-title">Note</p> from the div
          const title = element.querySelector("p.admonition-title");
          if (title) {
            element.removeChild(title);
          }
          console.log("Adding to actionNotes:", element.outerHTML);
          actionNotes.push(element.outerHTML);
        }
      }
    });
    console.log("actionDocu:", actionDocu);
    console.log("actionNotes:", actionNotes);
    return { actionDocu, actionNotes };
  });
}
