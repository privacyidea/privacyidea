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
import { computed, Signal, signal, WritableSignal } from "@angular/core";
import { of, Subject } from "rxjs";
import { FilterValue } from "../../app/core/models/filter_value";
import {
  ContainerDetailData,
  ContainerDetails,
  ContainerServiceInterface,
  ContainerTemplate,
  ContainerType,
  ContainerTypes
} from "../../app/services/container/container.service";
import { PiResponse } from "../../app/app.component";
import { Sort } from "@angular/material/sort";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockContainerService implements ContainerServiceInterface {
  compatibleWithSelectedTokenType = signal<string | null>(null);
  isPollingActive: Signal<boolean> = signal(false);
  apiFilter: string[] = [];
  advancedApiFilter: string[] = [];
  stopPolling$: Subject<void> = new Subject<void>();
  readonly containerBaseUrl = "mockEnvironment.proxyUrl + '/container'";
  eventPageSize: number = 10;
  states = signal<string[]>([]);
  readonly containerSerial = signal("CONT-1");
  readonly selectedContainer = signal("");
  readonly sort = signal<Sort>({ active: "serial", direction: "asc" });
  readonly containerFilter = signal<FilterValue>(new FilterValue());
  readonly filterParams = computed<Record<string, string>>(() =>
    Object.fromEntries(
      Object.entries(this.containerFilter()).filter(([key]) =>
        [...this.apiFilter, ...this.advancedApiFilter].includes(key)
      )
    )
  );
  pageSize = signal<number>(10);
  pageIndex = signal<number>(0);
  loadAllContainers = signal<boolean>(false);
  containerResource: MockHttpResourceRef<PiResponse<ContainerDetails> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue({ containers: [], count: 0 })
  );
  containerOptions: WritableSignal<string[]> = signal([]);
  filteredContainerOptions: Signal<string[]> = computed(() => {
    const options = this.containerOptions();
    const filter = this.containerFilter();
    return options.filter((option) => option.includes(filter.value) || option.includes(filter.hiddenValue));
  });
  containerSelection: WritableSignal<ContainerDetailData[]> = signal([]);
  containerTypesResource: MockHttpResourceRef<PiResponse<ContainerTypes, unknown> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue<ContainerTypes>(new Map())
  );
  containerTypeOptions: Signal<ContainerType[]> = computed(() => {
    return [
      { containerType: "generic", description: "", token_types: [] } as ContainerType,
      { containerType: "smartphone", description: "", token_types: [] } as ContainerType,
      { containerType: "yubikey", description: "", token_types: [] } as ContainerType
    ];
  });
  selectedContainerType = signal<ContainerType | undefined>(undefined);
  containerDetailResource = new MockHttpResourceRef(
    MockPiResponse.fromValue({
      containers: [
        {
          serial: "CONT-1",
          users: [{ user_realm: "", user_name: "", user_resolver: "", user_id: "" }],
          tokens: [],
          realms: [],
          states: [],
          type: "",
          select: "",
          description: "",
          info: {}
        }
      ],
      count: 1
    })
  );
  containerDetail = signal<ContainerDetails>({ containers: [], count: 0 });
  addToken = jest.fn().mockReturnValue(of(null));
  removeToken = jest.fn().mockReturnValue(of(null));
  setContainerRealm = jest.fn().mockReturnValue(of(null));
  setContainerDescription = jest.fn().mockReturnValue(of(null));
  toggleActive = jest.fn().mockReturnValue(of({}));
  unassignUser = jest.fn().mockReturnValue(of(null));
  assignUser = jest.fn().mockReturnValue(of(null));
  setContainerInfos = jest.fn().mockReturnValue(of({}));
  deleteInfo = jest.fn().mockReturnValue(of({}));
  addTokenToContainer = jest.fn().mockReturnValue(of(null));
  removeTokenFromContainer = jest.fn().mockReturnValue(of(null));
  toggleAll = jest.fn().mockReturnValue(of(null));
  removeAll = jest.fn().mockReturnValue(of(null));
  deleteContainer = jest.fn().mockReturnValue(of({}));
  deleteAllTokens = jest.fn().mockReturnValue(of(null));

  registerContainer(_params: { container_serial: string; passphrase_prompt: string; passphrase_response: string; }) {
    throw new Error("Method not implemented.");
  }

  readonly unregister = jest.fn().mockReturnValue(of({}));
  containerBelongsToUser = jest.fn().mockReturnValue(false);
  handleFilterInput = jest.fn();
  clearFilter = jest.fn();
  stopPolling = jest.fn();
  createContainer = jest.fn();
  startPolling = jest.fn();
  templatesResource: MockHttpResourceRef<PiResponse<{ templates: ContainerTemplate[] }, unknown> | undefined> =
    new MockHttpResourceRef(
      MockPiResponse.fromValue<{ templates: ContainerTemplate[] }>({ templates: [] })
    );
  templates: WritableSignal<ContainerTemplate[]> = signal([]);
  assignContainer = jest.fn().mockReturnValue(of(null));
  unassignContainer = jest.fn().mockReturnValue(of(null));
  pollContainerRolloutState = jest.fn();
  getContainerData = jest.fn().mockReturnValue(of({
    result: {
      value: {
        containers: [{
          serial: "CONT-1",
          users: [],
          tokens: [],
          realms: [],
          states: [],
          type: "",
          select: "",
          description: ""
        }, { serial: "CONT-2", users: [], tokens: [], realms: [], states: [], type: "", select: "", description: "" }],
        count: 2
      }
    }
  }));

  getContainerDetails(_containerSerial: string) {
    throw new Error("Method not implemented.");
  }
}
