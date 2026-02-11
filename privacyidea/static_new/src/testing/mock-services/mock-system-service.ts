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
import { computed, signal, Signal, WritableSignal } from "@angular/core";
import { Observable, of } from "rxjs";
import { HttpResourceRef } from "@angular/common/http";
import { PiNode, SystemServiceInterface } from "../../app/services/system/system.service";
import { CaConnectors } from "../../app/services/ca-connector/ca-connector.service";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

/**
 * function createMockHttpResource(result: any = []) {
 *   // Use a writable signal to store the value
 *   const valueSignal = signal({ result: { value: result } });
 *   return {
 *     value: () => valueSignal(),
 *     reload: jest.fn(),
 *     // Optionally allow tests to update the value
 *     setValue: (newResult: any) => valueSignal.set({ result: { value: newResult } })
 *   };
 * }
 *
 * export class MockSystemService implements SystemServiceInterface {
 *   nodes = signal<PiNode[]>([
 *     { name: "Node 1", uuid: "node-1" },
 *     { name: "Node 2", uuid: "node-2" }
 *   ]);
 *   systemConfig = signal({});
 *   nodesResource: any = {
 *     value: jest.fn().mockReturnValue({ result: { value: [] } }),
 *     reload: jest.fn()
 *   };
 *   radiusServerResource: any = {
 *     value: jest.fn().mockReturnValue({ result: { value: [] } }),
 *     reload: jest.fn()
 *   };
 *   systemConfigResource: any = {
 *     value: jest.fn().mockReturnValue({ result: { value: [] } }),
 *     reload: jest.fn()
 *   };
 * }
 * **/

export class MockSystemService implements SystemServiceInterface {
  systemConfigResource: HttpResourceRef<any>;
  radiusServerResource: HttpResourceRef<any>;
  nodesResource: HttpResourceRef<any>;
  systemConfig: Signal<any>;
  systemConfigInit: Signal<any>;
  nodes: Signal<PiNode[]>;

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

    const mockInit = {
      hashlibs: ["sha1", "sha256", "sha512"],
      totpSteps: [30, 60],
      smsProviders: ["provider1", "provider2"]
    };

    this.systemConfigResource = new MockHttpResourceRef(
      MockPiResponse.fromValue(mockConfig, {}, mockInit)
    );
    this.radiusServerResource = new MockHttpResourceRef(
      MockPiResponse.fromValue([])
    );
    this.nodesResource = new MockHttpResourceRef(
      MockPiResponse.fromValue<PiNode[]>([
        { name: "Node 1", uuid: "node-1" },
        { name: "Node 2", uuid: "node-2" }
      ])
    );
    this.systemConfig = computed(() => {
      return this.systemConfigResource.value()?.result?.value ?? {};
    });
    this.systemConfigInit = computed(() => {
      return this.systemConfigResource.value()?.result?.init ?? {};
    });
    this.nodes = computed<PiNode[]>(() => {
      return this.nodesResource.value()?.result?.value ?? [];
    });
  }

  caConnectorResource?: HttpResourceRef<any> | undefined;
    caConnectors?: WritableSignal<CaConnectors> | undefined;
    getDocumentation(): Observable<string> {
        throw new Error("Method not implemented.");
    }

  saveSystemConfig(config: any) {
    return of(MockPiResponse.fromValue({ status: true }));
  }

  deleteSystemConfig(key: string) {
    return of(MockPiResponse.fromValue({ status: true }));
  }

  deleteUserCache() {
    return of(MockPiResponse.fromValue({ status: true }));
  }

  loadSmtpIdentifiers() {
    return of(MockPiResponse.fromValue({ smtp1: "smtp1", smtp2: "smtp2" }));
  }
}