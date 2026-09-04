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
import { signal } from "@angular/core";
import { LANDING_PAGES, LandingPage } from "@core/landing-page";
import { UiPreferencesServiceInterface } from "@services/user-settings/ui-preferences.service";
import { of } from "rxjs";

export class MockUiPreferencesService implements UiPreferencesServiceInterface {
  readonly preferredLocale = signal("en");
  readonly showLoadingUrls = signal(false);
  readonly landingPage = signal<LandingPage>("tokens");
  readonly availableLandingPages = signal<LandingPage[]>(LANDING_PAGES);
  setShowLoadingUrls = jest.fn((show: boolean) => {
    this.showLoadingUrls.set(show);
    return of(null);
  });
  setLandingPage = jest.fn((page: LandingPage) => {
    this.landingPage.set(page);
  });
  resetLandingPage = jest.fn(() => of(null));
  landingPage$ = jest.fn(() => of(this.landingPage()));
  normalizeLocaleUrl = jest.fn();
  sync = jest.fn();
  switchLocale = jest.fn();
}
