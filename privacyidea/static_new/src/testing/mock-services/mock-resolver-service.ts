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

import { ResourceStatus, signal, Signal, WritableSignal } from "@angular/core";
import { Observable, of } from "rxjs";
import { Resolver, ResolverServiceInterface } from "../../app/services/resolver/resolver.service";
import { PiResponse } from "../../app/app.component";

export class MockResolverService implements ResolverServiceInterface {
  private _resolversValue: WritableSignal<Resolver[]> = signal([]);
  private _resolverOptionsValue: WritableSignal<string[]> = signal([]);
  resolversResource: any = {
    value: () => undefined,
    reload: jest.fn()
  };
  selectedResolverName: WritableSignal<string> = signal("");
  selectedResolverResource: any = {
    value: signal(undefined),
    status: signal(ResourceStatus.Resolved),
    reload: jest.fn()
  };
  resolvers: Signal<Resolver[]> = this._resolversValue.asReadonly();
  resolverOptions: Signal<string[]> = this._resolverOptionsValue.asReadonly();

  postResolverTest = jest.fn(() => of({} as PiResponse<any, any>));

  postResolver = jest.fn((resolverName: string, data: any) => of({} as PiResponse<any, any>));

  deleteResolver = jest.fn((resolverName: string) => of({} as PiResponse<any, any>));

  setResolvers(data: Resolver[]): void {
    this._resolversValue.set(data);
  }

  setResolverOptions(options: string[]): void {
    this._resolverOptionsValue.set(options);
  }
}
