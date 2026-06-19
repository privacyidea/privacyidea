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
import { PiResponse } from "@app/app.component";
import { Subscription } from "@services/subscription/subscription.service";
import { of } from "rxjs";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockSubscriptionService {
  reload = jest.fn();
  deleteSubscription = jest.fn(() => of(MockPiResponse.fromValue(true)));
  uploadSubscriptionFile = jest.fn(() => of(MockPiResponse.fromValue({})));
  subscriptionsResource = new MockHttpResourceRef<PiResponse<Record<string, Subscription>>>(
    MockPiResponse.fromValue({})
  );
}
