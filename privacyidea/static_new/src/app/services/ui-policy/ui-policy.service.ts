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
import { Injectable } from "@angular/core";

export interface AppConfig {
  remoteUser: string;
  forceRemoteUser: string;
  passwordReset: boolean;
  hsmReady: boolean;
  customization: string;
  realms: string;
  logo: string;
  showNode: string;
  externalLinks: boolean;
  hasJobQueue: string;
  loginText: string;
  logoutRedirectUrl: string;
  gdprLink: string;
  privacyideaVersionNumber: string;
  translationWarning: boolean;
  otpPinSetRandomUser?: number;
}

@Injectable({
  providedIn: "root"
})
export class UiPolicyService {
  private readonly config: AppConfig;

  constructor() {
    if (typeof window !== "undefined" && (window as any).appConfig) {
      this.config = (window as any).appConfig;
    } else {
      console.warn("App configuration not found. Using default values.");
      this.config = {
        remoteUser: "",
        forceRemoteUser: "",
        passwordReset: false,
        hsmReady: false,
        customization: "",
        realms: "",
        logo: "",
        showNode: "",
        externalLinks: false,
        hasJobQueue: "false",
        loginText: "",
        logoutRedirectUrl: "",
        gdprLink: "",
        privacyideaVersionNumber: "",
        translationWarning: false
      };
    }
  }

  get remoteUser(): string {
    return this.config.remoteUser;
  }

  get hasJobQueue(): boolean {
    return !!this.config.hasJobQueue.toLowerCase();
  }

  get passwordReset(): boolean {
    return this.config.passwordReset;
  }

  get hsmReady(): boolean {
    return this.config.hsmReady;
  }

  get customization(): string {
    return this.config.customization;
  }

  get realms(): string {
    return this.config.realms;
  }

  get logo(): string {
    return this.config.logo;
  }

  get showNode(): string {
    return this.config.showNode;
  }

  get externalLinks(): boolean {
    return this.config.externalLinks;
  }

  get loginText(): string {
    return this.config.loginText;
  }

  get logoutRedirectUrl(): string {
    return this.config.logoutRedirectUrl;
  }

  get gdprLink(): string {
    return this.config.gdprLink;
  }

  get privacyideaVersionNumber(): string {
    return this.config.privacyideaVersionNumber;
  }

  get translationWarning(): boolean {
    return this.config.translationWarning;
  }

  getConfig(): AppConfig {
    return this.config;
  }
}
