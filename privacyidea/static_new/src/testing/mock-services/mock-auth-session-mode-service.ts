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
import {
  AuthSessionMode,
  AuthSessionModeServiceInterface
} from "@services/auth-session-mode/auth-session-mode.service";

export class MockAuthSessionModeService implements AuthSessionModeServiceInterface {
  defaultMode: AuthSessionMode = "single-tab";
  mode = signal<AuthSessionMode>("single-tab");
  storage = signal<Storage>(sessionStorage);
  setMode = jest.fn().mockImplementation((mode: AuthSessionMode) => {
    this.mode.set(mode);
    this.storage.set(mode === "multi-tab-persistent" ? localStorage : sessionStorage);
  });
  setDefaultMode = jest.fn().mockImplementation(() => this.setMode(this.defaultMode));
  addModeChangeListener = jest.fn().mockReturnValue(jest.fn());
  adoptMode = jest.fn().mockImplementation((mode: AuthSessionMode) => {
    this.mode.set(mode);
    this.storage.set(mode === "multi-tab-persistent" ? localStorage : sessionStorage);
  });
}
