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
import { computed } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { SmsGateway, SmsGatewayServiceInterface, SmsProviders } from "@services/sms-gateway/sms-gateway.service";
import { MockHttpResourceRef, MockPiResponse } from "@testing/mock-services/mock-utils";

export class MockSmsGatewayService implements SmsGatewayServiceInterface {
  smsGatewayResource = new MockHttpResourceRef<PiResponse<SmsGateway[]> | undefined>(
    MockPiResponse.fromValue<SmsGateway[]>([])
  );

  smsProvidersResource = new MockHttpResourceRef<PiResponse<SmsProviders> | undefined>(
    MockPiResponse.fromValue<SmsProviders>({})
  );

  smsGateways = computed<SmsGateway[]>(() => []);
  postSmsGateway = jest.fn(async (): Promise<void> => Promise.resolve());
  deleteSmsGateway = jest.fn(async (): Promise<void> => Promise.resolve());
}
