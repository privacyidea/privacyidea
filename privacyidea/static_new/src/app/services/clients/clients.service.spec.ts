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

import { ClientsService } from "./clients.service";
import { AuditService } from "../audit/audit.service";
import {
  MockAuthService,
  MockContentService,
  MockLocalService,
  MockNotificationService
} from "../../../testing/mock-services";
import { TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { AuthService } from "../auth/auth.service";
import { ContentService } from "../content/content.service";

describe("ClientsService", () => {
  let clientService: ClientsService;
  let content: MockContentService;
  let authService: MockAuthService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        ClientsService,
        MockLocalService,
        MockNotificationService
      ]
    });
    clientService = TestBed.inject(ClientsService);
    content = TestBed.inject(ContentService) as any;
    authService = TestBed.inject(AuthService) as any;
  });

  it("should be created", () => {
    expect(clientService).toBeTruthy();
  });
});

