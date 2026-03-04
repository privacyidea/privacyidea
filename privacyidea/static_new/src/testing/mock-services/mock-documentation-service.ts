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

import { DocumentationServiceInterface } from "../../app/services/documentation/documentation.service";

export class MockDocumentationService implements DocumentationServiceInterface {
  openDocumentation = jest.fn().mockResolvedValue(undefined);
  getVersionUrl = jest.fn().mockReturnValue("https://example.com/versioned-docs/");
  getFallbackUrl = jest.fn().mockReturnValue("https://example.com/fallback-docs/");
  checkFullUrl = jest.fn().mockResolvedValue(true);
  checkPageUrl = jest.fn().mockResolvedValue("https://example.com/versioned-docs/");
  openDocumentationPage = jest.fn().mockResolvedValue(true);
  getPolicyActionDocumentation = jest.fn().mockResolvedValue({
    info: ["Doc Info"],
    notes: ["Doc Notes"]
  });
}
