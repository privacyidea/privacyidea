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
import {
  UserSettingKey,
  UserSettings,
  UserSettingsServiceInterface
} from "@services/user-settings/user-settings.service";
import { Observable, of } from "rxjs";

export class MockUserSettingsService implements UserSettingsServiceInterface {
  readonly settings = signal<UserSettings | null>({});

  getSettings(): Observable<UserSettings> {
    return of(this.settings() ?? {});
  }

  getSetting<T>(key: UserSettingKey): Observable<T | null> {
    return of((this.settings()?.[key] as T | undefined) ?? null);
  }

  setSetting<T>(key: UserSettingKey, value: T): Observable<UserSettings> {
    this.settings.update((settings) => ({ ...settings, [key]: value }));
    return of(this.settings() ?? {});
  }

  deleteSetting(key: UserSettingKey): Observable<UserSettings> {
    this.settings.update((settings) => {
      const remaining = { ...settings };
      delete remaining[key];
      return remaining;
    });
    return of(this.settings() ?? {});
  }

  clearCache(): void {
    this.settings.set({});
  }
}
