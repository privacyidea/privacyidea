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

import { signal } from "@angular/core";
import { PiNode, SystemServiceInterface } from "../../app/services/system/system.service";
import { HttpResourceRef } from "@angular/common/http";

function createMockHttpResource(result: any = []) {
  // Use a writable signal to store the value
  const valueSignal = signal({ result: { value: result } });
  return {
    value: () => valueSignal(),
    reload: jest.fn(),
    // Optionally allow tests to update the value
    setValue: (newResult: any) => valueSignal.set({ result: { value: newResult } })
  };
}

export class MockSystemService implements SystemServiceInterface {
  nodes = signal<PiNode[]>([{name: "node1", uuid: "1234-5678"}]);
  systemConfig = signal({});
  nodesResource: any = {
    value: jest.fn().mockReturnValue({ result: { value: [] } }),
    reload: jest.fn()
  };
  radiusServerResource: any = {
    value: jest.fn().mockReturnValue({ result: { value: [] } }),
    reload: jest.fn()
  };
  systemConfigResource: any = {
    value: jest.fn().mockReturnValue({ result: { value: [] } }),
    reload: jest.fn()
  };
}
