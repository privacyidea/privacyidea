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
import {
  PeriodicTask,
  PeriodicTaskOption,
  PeriodicTaskServiceInterface
} from "../../app/services/periodic-task/periodic-task.service";
import { of } from "rxjs";
import { PiResponse } from "../../app/app.component";
import { signal } from "@angular/core";

export class MockPeriodicTaskService implements PeriodicTaskServiceInterface {
  periodicTasksResource: any = {
    value: jest.fn().mockReturnValue({ result: { value: [] } }),
    reload: jest.fn()
  };
  periodicTaskModuleResource: any = {
    value: jest.fn().mockReturnValue({ result: { value: [] } }),
    reload: jest.fn()
  };
  moduleOptions = signal<Record<string, Record<string, PeriodicTaskOption>>>({
    "SimpleStats": {
      "hardware_tokens": { name: "hardware_tokens", type: "bool", description: "" },
      "assigned_tokens": {
        name: "assigned_tokens",
        description: "Number of tokens assigned to users",
        type: "bool"
      },
      "software_tokens": {
        name: "software_tokens",
        description: "Total number of software tokens",
        type: "bool"
      },
      "total_tokens": {
        name: "total_tokens",
        description: "Total number of tokens",
        type: "bool"
      }
    },
    "EventCounter": {
      "event_counter": {
        name: "event_counter",
        description: "The name of the event counter to read.",
        required: true,
        type: "str"
      },
      "reset_event_counter": {
        name: "reset_event_counter",
        description: "Whether to reset the event_counter, if it is read and written to the MonitoringStats table.",
        type: "bool"
      },
      "stats_key": {
        name: "stats_key",
        description: "The name of the stats key to write to the MonitoringStats table.",
        required: true,
        type: "str"
      }
    }
  })
  ;

  enablePeriodicTask = jest.fn().mockResolvedValue({});
  disablePeriodicTask = jest.fn().mockResolvedValue({});
  deletePeriodicTask = jest.fn().mockReturnValue(of({} as PiResponse<number, any>));
  deleteWithConfirmDialog = jest.fn();
  savePeriodicTask = jest.fn().mockReturnValue(of({} as PiResponse<PeriodicTask, any>));
  fetchAllModuleOptions = jest.fn();
}