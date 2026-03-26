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
import { PendingChangesServiceInterface } from "../../app/services/pending-changes/pending-changes.service";

export class MockPendingChangesService implements PendingChangesServiceInterface {
  hasChangesMockValue = false;
  validChangesMockValue = true;

  get hasChanges() {return this.hasChangesMockValue;};

  get validChanges() {return this.validChangesMockValue;};

  registerHasChanges = jest.fn();
  clearAllRegistrations = jest.fn();
  registerSave = jest.fn();
  save = jest.fn().mockReturnValue(true);
  registerValidChanges = jest.fn();
}
