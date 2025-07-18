import { Injectable } from '@angular/core';

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
  providedIn: 'root',
})
export class UiPolicyService {
  private readonly config: AppConfig;

  constructor() {
    if (typeof window !== 'undefined' && (window as any).appConfig) {
      this.config = (window as any).appConfig;
    } else {
      console.warn('App configuration not found. Using default values.');
      this.config = {
        remoteUser: '',
        forceRemoteUser: '',
        passwordReset: false,
        hsmReady: false,
        customization: '',
        realms: '',
        logo: '',
        showNode: '',
        externalLinks: false,
        hasJobQueue: 'false',
        loginText: '',
        logoutRedirectUrl: '',
        gdprLink: '',
        privacyideaVersionNumber: '',
        translationWarning: false,
      };
    }
  }

  getConfig(): AppConfig {
    return this.config;
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
}
