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
import { computed, signal, Signal, WritableSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import {
  EventActions,
  EventCondition,
  EventHandler,
  EventServiceInterface
} from "@services/event/event.service";
import { of } from "rxjs";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockEventService implements EventServiceInterface {
  selectedHandlerModule: WritableSignal<string | null> = signal(null);

  readonly allEventsResource = new MockHttpResourceRef<PiResponse<EventHandler[]> | undefined>(
    MockPiResponse.fromValue<EventHandler[]>([])
  );

  eventHandlers: WritableSignal<EventHandler[] | undefined> = signal([]);

  saveEventHandler = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<number>(1)));

  enableEvent = jest.fn().mockResolvedValue({});

  disableEvent = jest.fn().mockResolvedValue({});

  deleteEvent = jest.fn().mockReturnValue(of(MockPiResponse.fromValue<number>(1)));

  deleteWithConfirmDialog = jest.fn((_event: EventHandler, afterDelete?: () => void) => {
    if (afterDelete) afterDelete();
  });

  readonly eventHandlerModulesResource = new MockHttpResourceRef<PiResponse<string[]>>(
    MockPiResponse.fromValue<string[]>(["mockModule"])
  );

  eventHandlerModules: Signal<string[]> = computed(() => ["mockModule", "anotherModule"]);

  readonly availableEventsResource = new MockHttpResourceRef<PiResponse<string[]>>(
    MockPiResponse.fromValue<string[]>(["mockEvent"])
  );

  availableEvents: Signal<string[]> = computed(() => ["eventA", "eventAB", "eventB", "eventC"]);

  readonly modulePositionsResource = new MockHttpResourceRef<PiResponse<string[]>>(
    MockPiResponse.fromValue<string[]>(["mockPosition"])
  );

  modulePositions: Signal<string[]> = computed(() => ["pre", "post"]);

  readonly moduleActionsResource = new MockHttpResourceRef<PiResponse<EventActions>>(
    MockPiResponse.fromValue<EventActions>({})
  );

  moduleActions: Signal<EventActions> = computed(() => ({
    actionA: {
      opt1: { type: "bool", desc: "desc1", required: true },
      opt2: { type: "int", desc: "desc2", visibleIf: "opt1" },
      opt3: { type: "str", desc: "desc3", visibleIf: "opt2", visibleValue: 3 }
    },
    actionB: {
      opt3: { type: "text", desc: "desc3" }
    },
    add_token_info: {
      key: { type: "str", desc: "The key to add the token info under." },
      value: { type: "str", desc: "The value to add to the token info." }
    }
  }));

  readonly moduleConditionsResource = new MockHttpResourceRef<PiResponse<Record<string, EventCondition>>>(
    MockPiResponse.fromValue<Record<string, EventCondition>>({})
  );

  moduleConditions: Signal<Record<string, EventCondition>> = computed(() => ({
    condA: { type: "bool", desc: "descA" },
    condB: { type: "str", desc: "descB" },
    condC: { type: "int", desc: "descC", value: [1, 2, 3] },
    condD: { type: "multi", desc: "descD", value: [{ name: "option1" }, { name: "option2" }], group: "group1" }
  }));

  moduleConditionsByGroup: Signal<Record<string, Record<string, EventCondition>>> = computed(() => ({
    group1: {
      condA: { type: "bool", desc: "descA" },
      condB: { type: "str", desc: "descB" }
    },
    group2: {
      condC: { type: "int", desc: "descC" }
    }
  }));
}
