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

import { signal, Signal, WritableSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { Resolver, ResolverData, ResolverServiceInterface, Resolvers } from "@services/resolver/resolver.service";
import { of } from "rxjs";
import { MockHttpResourceRef } from "./mock-utils";

export class MockResolverService implements ResolverServiceInterface {
  private _resolversValue: WritableSignal<Resolver[]> = signal([]);
  private _resolverOptionsValue: WritableSignal<string[]> = signal([]);
  resolversResource = new MockHttpResourceRef<PiResponse<Resolvers> | undefined>(undefined);
  selectedResolverName: WritableSignal<string> = signal("");
  selectedResolverResource = new MockHttpResourceRef<PiResponse<Resolvers> | undefined>(undefined);
  resolvers: Signal<Resolver[]> = this._resolversValue.asReadonly();
  resolverOptions: Signal<string[]> = this._resolverOptionsValue.asReadonly();
  editableResolvers: WritableSignal<string[]> = signal([]);
  userAttributes: WritableSignal<string[]> = signal([]);

  postResolverTest = jest.fn(() => of({} as PiResponse<unknown>));

  postResolver = jest.fn((_resolverName: string, _data: ResolverData) => of({} as PiResponse<unknown>));

  deleteResolver = jest.fn((_resolverName: string) => of({} as PiResponse<unknown>));

  getDefaultResolverConfig = jest.fn((_resolverType: string) => of({} as PiResponse<unknown>));

  setResolvers(data: Resolver[]): void {
    this._resolversValue.set(data);
  }

  setResolverOptions(options: string[]): void {
    this._resolverOptionsValue.set(options);
  }
}
