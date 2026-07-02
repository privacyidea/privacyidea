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

import { TestBed } from "@angular/core/testing";
import { PendingChangesService } from "./pending-changes.service";

describe("PendingChangesService", () => {
  let service: PendingChangesService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [PendingChangesService]
    });
    service = TestBed.inject(PendingChangesService);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  describe("hasSaveFn", () => {
    it("should return false when no save function is registered", () => {
      expect(service.hasSaveFn).toBe(false);
    });

    it("should return true after a save function is registered", () => {
      service.registerSave(() => Promise.resolve(true));
      expect(service.hasSaveFn).toBe(true);
    });

    it("should return false again after clearAllRegistrations", () => {
      service.registerSave(() => Promise.resolve(true));
      service.clearAllRegistrations();
      expect(service.hasSaveFn).toBe(false);
    });
  });

  describe("hasChanges", () => {
    it("should return false when no hasChanges function is registered", () => {
      expect(service.hasChanges).toBe(false);
    });

    it("should return the result of the registered function", () => {
      service.registerHasChanges(() => true);
      expect(service.hasChanges).toBe(true);

      service.registerHasChanges(() => false);
      expect(service.hasChanges).toBe(false);
    });
  });

  describe("validChanges", () => {
    it("should return true by default", () => {
      expect(service.validChanges).toBe(true);
    });

    it("should return the result of the registered validChanges function", () => {
      service.registerValidChanges(() => false);
      expect(service.validChanges).toBe(false);
    });
  });

  describe("beforeunload", () => {
    function dispatchBeforeUnload(): boolean {
      const event = new Event("beforeunload", { cancelable: true });
      window.dispatchEvent(event);
      return event.defaultPrevented;
    }

    it("should not block unload when there are no pending changes", () => {
      expect(dispatchBeforeUnload()).toBe(false);
    });

    it("should block unload when there are pending changes", () => {
      service.registerHasChanges(() => true);
      expect(dispatchBeforeUnload()).toBe(true);
    });

    it("should stop blocking unload after the service is destroyed", () => {
      service.registerHasChanges(() => true);
      service.ngOnDestroy();
      expect(dispatchBeforeUnload()).toBe(false);
    });
  });
});
