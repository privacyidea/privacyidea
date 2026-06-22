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
import { computed, Signal, signal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { PiResponse } from "@app/app.component";
import { EnrollmentResponse, EnrollmentResponseDetail } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { FilterValue } from "@core/models/filter_value/filter_value";
import {
  BulkResult,
  LostTokenResponse,
  TokenDetails,
  Tokens,
  TokenService,
  TokenServiceInterface,
  TokenType,
  TokenTypeKey
} from "@services/token/token.service";
import { of, Subject } from "rxjs";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

function makeTokenDetailResponse(tokentype: TokenTypeKey): PiResponse<Tokens> {
  return MockPiResponse.fromValue<Tokens>({
    count: 1,
    current: 1,
    tokens: [
      {
        tokentype,
        active: true,
        revoked: false,
        container_serial: "",
        realms: [],
        count: 0,
        count_window: 0,
        description: "",
        failcount: 0,
        id: 0,
        info: {},
        locked: false,
        maxfail: 0,
        otplen: 0,
        resolver: "",
        rollout_state: "enrolled",
        serial: "X",
        sync_window: 0,
        tokengroup: [],
        user_id: "",
        user_realm: "",
        username: ""
      }
    ]
  });
}

export class MockTokenService implements TokenServiceInterface {
  tokenDetailResourceValue = signal<Tokens | undefined>(undefined);
  apiFilterKeyMap: Record<string, string> = {};
  stopPolling$ = new Subject<void>();
  tokenBaseUrl = "mockEnvironment.proxyUrl + '/token'";
  readonly maxDescriptionLength = 80;
  readonly eventPageSize = signal(10);
  tokenSerial = signal("");
  selectedTokenType = signal<TokenType>({
    key: "hotp",
    name: "HOTP",
    info: "",
    text: "HMAC-based One-Time Password"
  });
  showOnlyTokenNotInContainer = signal(false);
  tokenFilter = signal(new FilterValue());
  readonly tokenDetailResource = new MockHttpResourceRef<PiResponse<Tokens>>(makeTokenDetailResponse("hotp"));
  readonly tokenTypesResource = new MockHttpResourceRef<PiResponse<Record<string, string>> | undefined>(
    MockPiResponse.fromValue<Record<string, string>>({})
  );
  readonly userTokenResource = new MockHttpResourceRef<PiResponse<Tokens> | undefined>(
    MockPiResponse.fromValue<Tokens>({ count: 0, current: 0, tokens: [] })
  );
  detailsUser = signal({ username: "", realm: "" });
  tokenTypeOptions = signal<TokenType[]>([
    { key: "hotp", name: "HOTP", info: "", text: "HMAC-based One-Time Password" },
    { key: "totp", name: "TOTP", info: "", text: "Time-based One-Time Password" },
    { key: "push", name: "PUSH", info: "", text: "Push Notification" }
  ]);
  readonly pageSize = signal(10);
  readonly tokenIsActive = signal(true);
  readonly tokenIsRevoked = signal(false);
  defaultSizeOptions: number[] = [10, 25, 50];
  apiFilter: string[] = [];
  advancedApiFilter: string[] = [];
  sort = signal<Sort>({ active: "serial", direction: "asc" });
  readonly pageIndex = signal(0);
  readonly tokenResource = new MockHttpResourceRef<PiResponse<Tokens> | undefined>(undefined);
  tokenResourceValue = signal<Tokens | null>(null);
  readonly tokenSerialResource = new MockHttpResourceRef<PiResponse<Tokens> | undefined>(undefined);
  readonly tokenSelection = signal<TokenDetails[]>([]);
  selectedToken = signal<string | null>(null);
  tokenOptions = signal<string[]>([]);
  filteredTokenOptions: Signal<string[]> = computed(() => {
    const filter = (this.selectedToken() || "").toLowerCase();
    return this.tokenOptions().filter((option) => option.toLowerCase().includes(filter));
  });
  clearFilter = jest.fn();
  handleFilterInput = jest.fn();
  readonly toggleActive = jest.fn().mockReturnValue(of({}));
  readonly resetFailCount = jest.fn().mockReturnValue(of(null));
  readonly saveTokenDetail = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<boolean>(true)));
  getSerial = jest
    .fn()
    .mockReturnValue(of(MockPiResponse.fromValue<{ count: number; serial?: string }>({ count: 1, serial: "X" })));
  readonly setTokenInfos = jest.fn().mockReturnValue(of({}));
  readonly deleteToken = jest.fn().mockReturnValue(of({}));
  readonly bulkDeleteTokens = jest
    .fn()
    .mockReturnValue(of(MockPiResponse.fromValue<BulkResult>({ failed: [], unauthorized: [], count_success: 1 })));
  bulkDeleteWithConfirmDialog = jest.fn();
  readonly revokeToken = jest.fn().mockReturnValue(of({}));
  readonly deleteInfo = jest.fn().mockReturnValue(of({}));
  readonly unassignUserFromAll = jest.fn().mockReturnValue(of([]));
  readonly unassignUser = jest.fn().mockReturnValue(of(null));
  bulkUnassignTokens = jest
    .fn()
    .mockReturnValue(of(MockPiResponse.fromValue<BulkResult>({ failed: [], unauthorized: [], count_success: 1 })));
  readonly assignUserToAll = jest.fn().mockReturnValue(of([]));
  readonly assignUser = jest.fn().mockReturnValue(of(null));
  setPin = jest.fn();
  setRandomPin = jest.fn();
  readonly resyncOTPToken = jest.fn().mockReturnValue(of(null));
  readonly getTokenDetails = jest.fn().mockReturnValue(of({}));
  enrollToken = jest.fn().mockReturnValue(of({ detail: { serial: "X" } } as unknown as EnrollmentResponse));
  verifyToken = jest.fn().mockReturnValue(
    of(
      MockPiResponse.fromValue<boolean, EnrollmentResponseDetail>(true, {
        serial: "ABC123",
        rollout_state: "enrolled"
      } as EnrollmentResponseDetail)
    )
  );
  readonly lostToken = jest
    .fn<ReturnType<TokenService["lostToken"]>, Parameters<TokenService["lostToken"]>>()
    .mockImplementation((_serial: string) => {
      const response: LostTokenResponse = MockPiResponse.fromValue({
        disable: 1,
        end_date: "2025-01-31",
        init: true,
        password: "****",
        pin: false,
        serial: _serial,
        user: true,
        valid_to: "2025-02-28"
      });
      return of(response);
    });
  readonly stopPolling = jest.fn();
  readonly pollTokenRolloutState = jest.fn().mockReturnValue(of(makeTokenDetailResponse("hotp")));
  setTokenRealm = jest.fn();
  getTokengroups = jest.fn();
  setTokengroup = jest.fn();
  importTokens = jest.fn();
  hiddenApiFilter: string[] = [];
}
