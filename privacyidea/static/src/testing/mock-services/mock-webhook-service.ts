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
import { computed, signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { Webhook, WebhookTestResult } from "@services/webhook/webhook.service";
import { of } from "rxjs";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockWebhookService {
  webhookResource = new MockHttpResourceRef<PiResponse<Webhook[]> | undefined>(MockPiResponse.fromValue<Webhook[]>([]));
  webhooks = signal<Webhook[]>([]);
  webhookIdentifiers = computed<string[]>(() => this.webhooks().map((webhook) => webhook.identifier));
  postWebhook = jest.fn(async (): Promise<void> => Promise.resolve());
  testWebhook = jest.fn(async (): Promise<WebhookTestResult | null> =>
    Promise.resolve({ success: true, status_code: 200, response: "", error: null })
  );
  deleteWebhook = jest.fn(async (): Promise<void> => Promise.resolve());
  listWebhooks = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<Webhook[]>([])));
}
