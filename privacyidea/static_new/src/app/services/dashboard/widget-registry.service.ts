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
import { Injectable } from "@angular/core";
import { StatWidgetComponent } from "@components/dashboard/widgets/stat-widget/stat-widget.component";
import { WelcomeWidgetComponent } from "@components/dashboard/widgets/welcome-widget/welcome-widget.component";
import { WidgetDefinition } from "@models/dashboard";

export interface WidgetRegistryServiceInterface {
  readonly definitions: WidgetDefinition[];

  get(type: string): WidgetDefinition | undefined;
}

@Injectable({
  providedIn: "root"
})
export class WidgetRegistryService implements WidgetRegistryServiceInterface {
  private readonly registry = new Map<string, WidgetDefinition>();

  public readonly definitions: WidgetDefinition[] = [
    {
      type: "welcome",
      title: $localize`Welcome`,
      icon: "waving_hand",
      component: WelcomeWidgetComponent,
      defaultSize: { cols: 8, rows: 4 },
      minSize: { cols: 4, rows: 2 }
    },
    {
      type: "stat",
      title: $localize`Statistic`,
      icon: "insights",
      component: StatWidgetComponent,
      defaultSize: { cols: 4, rows: 4 },
      minSize: { cols: 2, rows: 2 }
    }
  ];

  constructor() {
    this.definitions.forEach((definition) => this.registry.set(definition.type, definition));
  }

  public get(type: string): WidgetDefinition | undefined {
    return this.registry.get(type);
  }
}
