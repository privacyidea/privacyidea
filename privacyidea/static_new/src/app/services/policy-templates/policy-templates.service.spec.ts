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
import { POLICY_TEMPLATE_INDEX, POLICY_TEMPLATES } from "./policy-templates.constants";
import { PolicyTemplatesService } from "./policy-templates.service";

describe("PolicyTemplatesService", () => {
  let service: PolicyTemplatesService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [PolicyTemplatesService] });
    service = TestBed.inject(PolicyTemplatesService);
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  it("exposes the policy templates index as a signal", () => {
    expect(service.policyTemplatesIndex()).toEqual(POLICY_TEMPLATE_INDEX);
  });

  it("returns a known template by name", () => {
    expect(service.getTemplate("webui1")).toEqual(POLICY_TEMPLATES["webui1"]);
  });

  it("returns undefined for an unknown template name", () => {
    expect(service.getTemplate("does-not-exist")).toBeUndefined();
  });

  it("ships every template that the index references", () => {
    for (const name of Object.keys(POLICY_TEMPLATE_INDEX)) {
      expect(service.getTemplate(name)).toBeDefined();
    }
  });

  it("uses matching names inside the template payload", () => {
    for (const [name, template] of Object.entries(POLICY_TEMPLATES)) {
      expect(template.name).toBe(name);
    }
  });
});
