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
import {
  EventActions,
  EventCondition,
  EventHandler,
  EventServiceInterface
} from "../../app/services/event/event.service";
import { computed, signal, Signal, WritableSignal } from "@angular/core";
import { of } from "rxjs";
import { HttpResourceRef } from "@angular/common/http";
import { PiResponse } from "../../app/app.component";

export class MockEventService implements EventServiceInterface {
  selectedHandlerModule: WritableSignal<string | null> = signal(null);

  readonly allEventsResource: HttpResourceRef<PiResponse<EventHandler[]> | undefined> = {
    value: jest.fn(() => ({ result: { value: [] } })),
    reload: jest.fn()
  } as any;

  eventHandlers: Signal<EventHandler[] | undefined> = computed(() => []);

  saveEventHandler = jest.fn((event: Record<string, any>) => of({ result: { value: 1 } } as PiResponse<number, any>));

  enableEvent = jest.fn((eventId: string) => Promise.resolve({}));

  disableEvent = jest.fn((eventId: string) => Promise.resolve({}));

  deleteEvent = jest.fn((eventId: string) => of({ result: { value: 1 } } as PiResponse<number, any>));

  deleteWithConfirmDialog = jest.fn((event: EventHandler, dialog: any, afterDelete?: () => void) => {
    if (afterDelete) afterDelete();
  });

  readonly eventHandlerModulesResource: HttpResourceRef<PiResponse<string[]> | undefined> = {
    value: jest.fn(() => ({ result: { value: ["mockModule"] } }))
  } as any;

  eventHandlerModules: Signal<string[]> = computed(() => ["mockModule", "anotherModule"]);

  readonly availableEventsResource: HttpResourceRef<PiResponse<string[]> | undefined> = {
    value: jest.fn(() => ({ result: { value: ["mockEvent"] } }))
  } as any;

  availableEvents: Signal<string[]> = computed(() => ["eventA", "eventAB", "eventB", "eventC"]);

  readonly modulePositionsResource: HttpResourceRef<PiResponse<string[]> | undefined> = {
    value: jest.fn(() => ({ result: { value: ["mockPosition"] } }))
  } as any;

  modulePositions: Signal<string[]> = computed(() => ["pre", "post"]);

  readonly moduleActionsResource: HttpResourceRef<PiResponse<EventActions> | undefined> = {
    value: jest.fn(() => ({ result: { value: {} } }))
  } as any;

  moduleActions: Signal<EventActions> = computed(() => ({
    actionA: {
      opt1: { type: "bool", desc: "desc1", required: true },
      opt2: { type: "int", desc: "desc2", visibleIf: "opt1"},
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

  readonly moduleConditionsResource: HttpResourceRef<PiResponse<Record<string, EventCondition>> | undefined> = {
    value: jest.fn(() => ({ result: { value: {} } }))
  } as any;

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