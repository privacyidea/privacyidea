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
import { HttpResourceRef } from "@angular/common/http";
import { signal, WritableSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { CaConnectors } from "@services/ca-connector/ca-connector.service";
import {
  NodeInfo,
  SystemConfigInit,
  SystemConfigResponse,
  SystemServiceInterface
} from "@services/system/system.service";
import { Observable, of } from "rxjs";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockSystemService implements SystemServiceInterface {
  systemConfigResource: HttpResourceRef<SystemConfigResponse | undefined>;
  radiusServerResource: HttpResourceRef<PiResponse<string[]> | undefined>;
  nodesResource: HttpResourceRef<PiResponse<NodeInfo[]> | undefined>;
  systemConfig: WritableSignal<Record<string, string>>;
  systemConfigInit: WritableSignal<SystemConfigInit>;
  nodes: WritableSignal<NodeInfo[]>;

  constructor() {
    const mockConfig: Record<string, string> = {
      splitAtSign: "True",
      IncFailCountOnFalsePin: "False",
      no_auth_counter: "True",
      PrependPin: "False",
      ReturnSamlAttributes: "True",
      ReturnSamlAttributesOnFail: "False",
      AutoResync: "True",
      UiLoginDisplayHelpButton: "False",
      UiLoginDisplayRealmBox: "True",
      someOtherConfig: "test_value"
    };

    const mockInit: SystemConfigInit = {
      hashlibs: ["sha1", "sha256", "sha512"],
      totpSteps: [30, 60],
      smsProviders: ["provider1", "provider2"]
    };

    const mockNodes: NodeInfo[] = [
      { name: "Node 1", uuid: "node-1" },
      { name: "Node 2", uuid: "node-2" }
    ];

    this.systemConfigResource = new MockHttpResourceRef(
      MockPiResponse.fromValue<Record<string, string>, unknown, SystemConfigInit>(mockConfig, {}, mockInit)
    ) as unknown as HttpResourceRef<SystemConfigResponse | undefined>;
    this.radiusServerResource = new MockHttpResourceRef<PiResponse<string[]> | undefined>(
      MockPiResponse.fromValue<string[]>([])
    );
    this.nodesResource = new MockHttpResourceRef<PiResponse<NodeInfo[]> | undefined>(
      MockPiResponse.fromValue<NodeInfo[]>(mockNodes)
    );
    this.systemConfig = signal<Record<string, string>>(mockConfig);
    this.systemConfigInit = signal<SystemConfigInit>(mockInit);
    this.nodes = signal<NodeInfo[]>(mockNodes);
  }
  radiusServers = signal<string[]>([]);

  caConnectorResource?: HttpResourceRef<PiResponse<CaConnectors> | undefined>;
  caConnectors?: WritableSignal<CaConnectors>;

  getDocumentation(): Observable<string> {
    throw new Error("Method not implemented.");
  }

  saveSystemConfig = jest.fn(() => of(MockPiResponse.fromValue<Record<string, "insert" | "update">>({})));
  deleteSystemConfig = jest.fn(() => of(MockPiResponse.fromValue(true)));
  deleteUserCache = jest.fn(() => of(MockPiResponse.fromValue({ status: true, deleted: 0 })));
  loadSmtpIdentifiers = jest.fn(() => of(MockPiResponse.fromValue({ smtp1: "smtp1", smtp2: "smtp2" })));
}
