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
import { TestBed } from "@angular/core/testing";
import { VersioningService } from "./version.service";

describe("VersioningService", () => {
  let service: VersioningService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [VersioningService]
    });
    service = TestBed.inject(VersioningService);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("should have an initial empty version", () => {
    expect(service.version()).toBe("");
  });

  it("should return an empty string for getVersion() initially", () => {
    expect(service.getVersion()).toBe("");
  });

  it("should update the version signal", () => {
    const newVersion = "1.2.3";
    service.version.set(newVersion);
    expect(service.version()).toBe(newVersion);
  });

  it("should return the updated version from getVersion()", () => {
    const newVersion = "4.5.6";
    service.version.set(newVersion);
    expect(service.getVersion()).toBe(newVersion);
  });
});
