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
import { signal } from "@angular/core";
import { DetailFieldHandle, DetailsEditRegistry } from "./details-edit-registry.service";

function makeHandle(editing: boolean) {
  const isEditing = signal(editing);
  const handle: DetailFieldHandle = {
    isEditing,
    save: jest.fn(),
    cancel: jest.fn()
  };
  return { handle, isEditing };
}

describe("DetailsEditRegistry", () => {
  let registry: DetailsEditRegistry;

  beforeEach(() => {
    registry = new DetailsEditRegistry();
  });

  it("anyEditing reflects registered handles", () => {
    const a = makeHandle(false);
    const b = makeHandle(false);
    registry.register(a.handle);
    registry.register(b.handle);

    expect(registry.anyEditing()).toBe(false);

    b.isEditing.set(true);
    expect(registry.anyEditing()).toBe(true);

    b.isEditing.set(false);
    expect(registry.anyEditing()).toBe(false);
  });

  it("saveAll saves only editing handles", async () => {
    const a = makeHandle(true);
    const b = makeHandle(false);
    registry.register(a.handle);
    registry.register(b.handle);

    await registry.saveAll();

    expect(a.handle.save).toHaveBeenCalledTimes(1);
    expect(b.handle.save).not.toHaveBeenCalled();
  });

  it("cancelAll cancels only editing handles", () => {
    const a = makeHandle(true);
    const b = makeHandle(false);
    registry.register(a.handle);
    registry.register(b.handle);

    registry.cancelAll();

    expect(a.handle.cancel).toHaveBeenCalledTimes(1);
    expect(b.handle.cancel).not.toHaveBeenCalled();
  });

  it("unregister removes a handle from aggregation", () => {
    const a = makeHandle(true);
    registry.register(a.handle);
    expect(registry.anyEditing()).toBe(true);

    registry.unregister(a.handle);
    expect(registry.anyEditing()).toBe(false);
  });
});
