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
  ConditionalAccessPolicyServiceInterface,
  LockoutPolicy
} from "@services/conditional-access/conditional-access-policy.service";
import { MockHttpResourceRef, MockPiResponse } from "@testing/mock-services/mock-utils";

export class MockConditionalAccessPolicyService implements ConditionalAccessPolicyServiceInterface {
  policiesResource = new MockHttpResourceRef(MockPiResponse.fromValue<LockoutPolicy[]>([]));

  policies = signal<LockoutPolicy[]>([]);

  savePolicy = jest.fn(async (): Promise<number | undefined> => Promise.resolve(1));

  deletePolicy = jest.fn(async (): Promise<void> => Promise.resolve());

  deleteWithConfirmDialog = jest.fn(async (): Promise<void> => Promise.resolve());

  enablePolicy = jest.fn(async (): Promise<void> => Promise.resolve());

  disablePolicy = jest.fn(async (): Promise<void> => Promise.resolve());
}
