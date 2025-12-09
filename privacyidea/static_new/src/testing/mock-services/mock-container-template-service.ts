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
import { PiResponse } from "../../app/app.component";
import {
  ContainerTemplateServiceInterface,
  TemplateTokenTypes
} from "../../app/services/container-template/container-template.service";
import { ContainerTemplate } from "../../app/services/container/container.service";
import { MockHttpResourceRef } from "../mock-services";

export class MockContainerTemplateService implements ContainerTemplateServiceInterface {
  containerTemplateBaseUrl: string = "/mock/container/templates/";
  templatesResource = new MockHttpResourceRef<PiResponse<{ templates: ContainerTemplate[] }, unknown> | undefined>(
    undefined
  );
  templates = signal<ContainerTemplate[]>([]);
  templateTokenTypesResource = new MockHttpResourceRef<PiResponse<TemplateTokenTypes, unknown> | undefined>(undefined);
  templateTokenTypes = signal<TemplateTokenTypes>({});
  availableContainerTypes = signal<string[]>([]);
  getTokenTypesForContainerType = jest.fn(() => []);
  emptyContainerTemplate: ContainerTemplate = {
    name: "",
    container_type: "",
    default: false,
    template_options: {
      options: undefined,
      tokens: []
    }
  };
  deleteTemplate = jest.fn();
  postTemplateEdits = jest.fn();
  canSaveTemplate = jest.fn();
}
