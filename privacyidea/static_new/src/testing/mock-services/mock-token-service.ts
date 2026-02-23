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
import { HttpParams } from "@angular/common/http";
import { Signal, signal, WritableSignal } from "@angular/core";
import { Sort } from "@angular/material/sort";
import { of, Subject } from "rxjs";
import { FilterValue } from "../../app/core/models/filter_value";
import { BulkResult, LostTokenResponse, TokenDetails, Tokens, TokenService, TokenServiceInterface, TokenType } from "../../app/services/token/token.service";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";
import { PiResponse } from "../../app/app.component";

function makeTokenDetailResponse(tokentype: string): PiResponse<Tokens> {
  return {
    id: 0,
    jsonrpc: "2.0",
    signature: "",
    time: Date.now(),
    version: "1.0",
    versionnumber: "1.0",
    detail: {},
    result: {
      status: true,
      value: {
        count: 1,
        current: 1,
        tokens: [
          {
            tokentype: tokentype as any,
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
            rollout_state: "",
            serial: "X",
            sync_window: 0,
            tokengroup: [],
            user_id: "",
            user_realm: "",
            username: ""
          }
        ]
      }
    }
  } as any;
}

export class MockTokenService implements TokenServiceInterface {
  apiFilterKeyMap: Record<string, string> = {};
  stopPolling$: Subject<void> = new Subject<void>();
  tokenBaseUrl: string = "mockEnvironment.proxyUrl + '/token'";
  readonly eventPageSize = 10;
  tokenSerial = signal("");
  selectedTokenType: WritableSignal<TokenType> = signal({ key: "hotp", name: "HOTP", info: "", text: "HMAC-based One-Time Password" });
  showOnlyTokenNotInContainer = signal(false);
  tokenFilter: WritableSignal<FilterValue> = signal(new FilterValue());
  readonly tokenDetailResource = new MockHttpResourceRef<PiResponse<Tokens>>(makeTokenDetailResponse("hotp"));
  readonly tokenTypesResource = new MockHttpResourceRef<PiResponse<{}, unknown> | undefined>(MockPiResponse.fromValue({}));
  readonly userTokenResource = new MockHttpResourceRef<PiResponse<Tokens> | undefined>(
    MockPiResponse.fromValue<Tokens>({ count: 0, current: 0, tokens: [] })
  );
  detailsUsername: WritableSignal<string> = signal("");
  userRealm = signal("");
  tokenTypeOptions: WritableSignal<TokenType[]> = signal<TokenType[]>([
    { key: "hotp", name: "HOTP", info: "", text: "HMAC-based One-Time Password" },
    { key: "totp", name: "TOTP", info: "", text: "Time-based One-Time Password" },
    { key: "push", name: "PUSH", info: "", text: "Push Notification" }
  ]);
  readonly pageSize = signal(10);
  readonly tokenIsActive: WritableSignal<boolean> = signal(true);
  readonly tokenIsRevoked: WritableSignal<boolean> = signal(false);
  defaultSizeOptions: number[] = [10, 25, 50];
  apiFilter: string[] = [];
  advancedApiFilter: string[] = [];
  sort: WritableSignal<Sort> = signal({ active: "serial", direction: "asc" });
  readonly pageIndex = signal(0);
  readonly tokenResource = new MockHttpResourceRef<PiResponse<Tokens> | undefined>(undefined as any);
  readonly tokenSelection: WritableSignal<TokenDetails[]> = signal<TokenDetails[]>([]);
  clearFilter = jest.fn();
  handleFilterInput = jest.fn();
  readonly toggleActive = jest.fn().mockReturnValue(of({}));
  readonly resetFailCount = jest.fn().mockReturnValue(of(null));
  readonly saveTokenDetail = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<boolean>(true)));

  getSerial(_otp: string, _params: HttpParams) {
    throw new Error("Method not implemented.");
  }

  readonly setTokenInfos = jest.fn().mockReturnValue(of({}));
  readonly deleteToken = jest.fn().mockReturnValue(of({}));
  readonly bulkDeleteTokens = jest.fn().mockReturnValue(
    of(MockPiResponse.fromValue<BulkResult>({ failed: [], unauthorized: [], count_success: 1 }))
  );
  bulkDeleteWithConfirmDialog = jest.fn();
  readonly revokeToken = jest.fn().mockReturnValue(of({}));
  readonly deleteInfo = jest.fn().mockReturnValue(of({}));
  readonly unassignUserFromAll = jest.fn().mockReturnValue(of([]));
  readonly unassignUser = jest.fn().mockReturnValue(of(null));

  bulkUnassignTokens(_tokenDetails: TokenDetails[]) {
    throw new Error("Method not implemented.");
  }

  readonly assignUserToAll = jest.fn().mockReturnValue(of([]));
  readonly assignUser = jest.fn().mockReturnValue(of(null));
  setPin = jest.fn();
  setRandomPin = jest.fn();
  readonly resyncOTPToken = jest.fn().mockReturnValue(of(null));
  readonly getTokenDetails = jest.fn().mockReturnValue(of({}));
  readonly enrollToken = jest.fn().mockReturnValue(of({ detail: { serial: "X" } } as any));
  readonly lostToken = jest
    .fn<ReturnType<TokenService["lostToken"]>, Parameters<TokenService["lostToken"]>>()
    .mockImplementation((_serial: string) => {
      const response: LostTokenResponse = {
        id: 0,
        jsonrpc: "2.0",
        signature: "",
        time: Date.now(),
        version: "1.0",
        versionnumber: "1.0",
        detail: {},
        result: {
          status: true,
          value: { disable: 1, end_date: "2025-01-31", init: true, password: "****", pin: false, serial: _serial, user: true, valid_to: "2025-02-28" }
        }
      } as any;
      return of(response);
    });
  readonly stopPolling = jest.fn();
  readonly pollTokenRolloutState = jest.fn().mockReturnValue(of({ result: { status: true, value: { tokens: [{ rollout_state: "enrolled" }] } } } as any));
  setTokenRealm = jest.fn();
  getTokengroups = jest.fn();
  setTokengroup = jest.fn();
  importTokens = jest.fn();
  hiddenApiFilter: string[] = [];
}
