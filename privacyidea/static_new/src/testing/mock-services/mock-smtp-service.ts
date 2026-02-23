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
import { HttpResourceRef } from "@angular/common/http";
import { PiResponse } from "../../app/app.component";
import { SmtpServer, SmtpServers } from "../../app/services/smtp/smtp.service";

export class MockSmtpService {
  smtpServerResource: HttpResourceRef<PiResponse<SmtpServers> | undefined> = {
    value: signal(undefined),
    status: signal(0) as any,
    error: signal(null),
    isLoading: signal(false),
    reload: jest.fn(),
    headers: signal(undefined),
    statusCode: signal(undefined),
    progress: signal(undefined),
    hasValue: function (): this is HttpResourceRef<Exclude<PiResponse<SmtpServers> | undefined, undefined>> {
      return this.value() !== undefined;
    },
    destroy: function (): void {}
  } as any;

  smtpServers = computed<SmtpServer[]>(() => []);

  postSmtpServer = jest.fn(async (_server: SmtpServer): Promise<void> => {
    return Promise.resolve();
  });

  testSmtpServer = jest.fn(async (_params: any): Promise<boolean> => {
    return Promise.resolve(true);
  });

  deleteSmtpServer = jest.fn(async (_identifier: string): Promise<void> => {
    return Promise.resolve();
  });
}
