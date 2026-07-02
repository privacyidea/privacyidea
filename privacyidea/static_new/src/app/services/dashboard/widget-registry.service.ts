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
import { AdministrationWidgetComponent } from "@components/dashboard/widgets/administration-widget/administration-widget.component";
import { AuthenticationsWidgetComponent } from "@components/dashboard/widgets/authentications-widget/authentications-widget.component";
import { EventsWidgetComponent } from "@components/dashboard/widgets/events-widget/events-widget.component";
import { PoliciesWidgetComponent } from "@components/dashboard/widgets/policies-widget/policies-widget.component";
import { SubscriptionsWidgetComponent } from "@components/dashboard/widgets/subscriptions-widget/subscriptions-widget.component";
import { TokenTypesWidgetComponent } from "@components/dashboard/widgets/token-types-widget/token-types-widget.component";
import { TokensWidgetComponent } from "@components/dashboard/widgets/tokens-widget/tokens-widget.component";
import { WidgetComponentType } from "@models/dashboard";

export interface WidgetRegistryServiceInterface {
  readonly widgetTypes: WidgetComponentType[];

  get(type: string): WidgetComponentType | undefined;
}

@Injectable({
  providedIn: "root"
})
export class WidgetRegistryService implements WidgetRegistryServiceInterface {
  public readonly widgetTypes: WidgetComponentType[] = [
    TokensWidgetComponent,
    TokenTypesWidgetComponent,
    AuthenticationsWidgetComponent,
    AdministrationWidgetComponent,
    PoliciesWidgetComponent,
    EventsWidgetComponent,
    SubscriptionsWidgetComponent
  ];

  private readonly byType = new Map<string, WidgetComponentType>(
    this.widgetTypes.map((widget) => [widget.type, widget])
  );

  public get(type: string): WidgetComponentType | undefined {
    return this.byType.get(type);
  }
}
