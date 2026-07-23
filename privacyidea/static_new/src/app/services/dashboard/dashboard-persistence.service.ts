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
import { inject, Injectable } from "@angular/core";
import { WidgetInstance } from "@models/dashboard";
import { UserSettingsService, UserSettingsServiceInterface } from "@services/user-settings/user-settings.service";
import { catchError, map, Observable, of } from "rxjs";

/** Shape of the "dashboard" key inside the user settings document. */
export interface DashboardSetting {
  widgets: WidgetInstance[];
}

export interface DashboardPersistenceServiceInterface {
  load(): Observable<WidgetInstance[] | null>;

  save(widgets: WidgetInstance[]): Observable<void>;
}

@Injectable({
  providedIn: "root"
})
export class DashboardPersistenceService implements DashboardPersistenceServiceInterface {
  private readonly userSettings: UserSettingsServiceInterface = inject(UserSettingsService);

  public load(): Observable<WidgetInstance[] | null> {
    return this.userSettings.getSetting<DashboardSetting>("dashboard").pipe(
      map((setting) => this.readWidgets(setting)),
      catchError(() => of(null))
    );
  }

  public save(widgets: WidgetInstance[]): Observable<void> {
    return this.userSettings.setSetting<DashboardSetting>("dashboard", { widgets }).pipe(
      map(() => undefined),
      catchError(() => of(undefined))
    );
  }

  private readWidgets(setting: DashboardSetting | null): WidgetInstance[] | null {
    const widgets = setting?.widgets;
    if (!Array.isArray(widgets)) {
      return null;
    }
    return widgets.filter((widget) => this.isWidgetInstance(widget));
  }

  private isWidgetInstance(widget: unknown): widget is WidgetInstance {
    const candidate = widget as Partial<WidgetInstance> | null;
    return (
      !!candidate &&
      typeof candidate.id === "string" &&
      typeof candidate.type === "string" &&
      [candidate.x, candidate.y, candidate.cols, candidate.rows].every(
        (value) => typeof value === "number" && Number.isFinite(value)
      )
    );
  }
}
