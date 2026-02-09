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
import { computed, Signal } from "@angular/core";
import { of } from "rxjs";
import { HttpResourceRef } from "@angular/common/http";
import { MockHttpResourceRef, MockPiResponse } from "../mock-services";
import { SystemServiceInterface } from "../../app/services/system/system.service";

export class MockSystemService implements SystemServiceInterface {
  systemConfigResource: HttpResourceRef<any>;
  radiusServerResource: HttpResourceRef<any>;
  nodesResource: HttpResourceRef<any>;
  systemConfig: Signal<any>;
  nodes: Signal<any>;

  constructor() {
    const mockConfig = {
      splitAtSign: true,
      IncFailCountOnFalsePin: false,
      no_auth_counter: true,
      PrependPin: false,
      ReturnSamlAttributes: true,
      ReturnSamlAttributesOnFail: false,
      AutoResync: true,
      UiLoginDisplayHelpButton: false,
      UiLoginDisplayRealmBox: true,
      someOtherConfig: "test_value"
    };

    this.systemConfigResource = new MockHttpResourceRef(
      MockPiResponse.fromValue(mockConfig)
    );
    this.radiusServerResource = new MockHttpResourceRef(
      MockPiResponse.fromValue({})
    );
    this.nodesResource = new MockHttpResourceRef(
      MockPiResponse.fromValue([])
    );
    this.systemConfig = computed(() => {
      return this.systemConfigResource.value()?.result?.value ?? {};
    });
    this.nodes = computed(() => {
      return this.nodesResource.value()?.result?.value ?? [];
    });
  }

  saveSystemConfig(config: any) {
    return of(MockPiResponse.fromValue({ status: true }));
  }

  deleteUserCache() {
    return of(MockPiResponse.fromValue({ status: true }));
  }

  loadSmtpIdentifiers() {
    return of(MockPiResponse.fromValue({ smtp1: "smtp1", smtp2: "smtp2" }));
  }
}