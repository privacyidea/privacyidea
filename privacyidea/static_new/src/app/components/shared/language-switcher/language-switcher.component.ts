/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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
import { Component, inject, LOCALE_ID } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatMenuModule } from "@angular/material/menu";
import { MatTooltipModule } from "@angular/material/tooltip";
import { localeTargetUrl, markLocaleAttempt, normalizeLocale, rememberLocale, UI_LOCALES } from "@core/locale";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { UserSettingsService, UserSettingsServiceInterface } from "@services/user-settings/user-settings.service";

@Component({
  selector: "app-language-switcher",
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatMenuModule, MatTooltipModule],
  templateUrl: "./language-switcher.component.html"
})
export class LanguageSwitcherComponent {
  private readonly localeId = inject(LOCALE_ID);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly userSettingsService: UserSettingsServiceInterface = inject(UserSettingsService);
  protected readonly locales = UI_LOCALES;
  protected readonly currentLocale = normalizeLocale(this.localeId);

  protected switchTo(code: string): void {
    if (code === this.currentLocale) {
      return;
    }
    rememberLocale(code);
    markLocaleAttempt(code);
    const target = localeTargetUrl(code);
    if (!this.authService.isAuthenticated()) {
      this.navigate(target);
      return;
    }
    // Each locale is a separately compiled bundle, so applying a language is a full-page
    // navigation -- which cancels in-flight requests. Store the preference first and only
    // navigate once the request settled, otherwise the setting would be lost.
    this.userSettingsService.setSetting("locale", code).subscribe({
      next: () => this.navigate(target),
      error: () => this.navigate(target)
    });
  }

  protected navigate(url: string): void {
    window.location.assign(url);
  }
}
