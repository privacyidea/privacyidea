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

import { HttpResourceRef } from "@angular/common/http";
import { signal, WritableSignal, Signal } from "@angular/core";
import { PiResponse } from "src/app/app.component";
import {
  ContainerTemplateServiceInterface,
  TemplateTokenTypes
} from "src/app/services/container-template/container-template.service";
import { ContainerTemplate } from "src/app/services/container/container.service";
import { MockHttpResourceRef } from "./mock-utils";

export class MockContainerTemplateService implements ContainerTemplateServiceInterface {
  // --- Properties ---
  containerTemplateBaseUrl: string = "/mock/container/templates/";

  templatesResource = new MockHttpResourceRef<PiResponse<{ templates: ContainerTemplate[] }, unknown> | undefined>(
    undefined
  ) as unknown as HttpResourceRef<PiResponse<{ templates: ContainerTemplate[] }, unknown> | undefined>;

  templates = signal<ContainerTemplate[]>([]) as WritableSignal<ContainerTemplate[]>;

  templateTokenTypesResource = new MockHttpResourceRef<PiResponse<TemplateTokenTypes, unknown> | undefined>(
    undefined
  ) as unknown as HttpResourceRef<PiResponse<TemplateTokenTypes, unknown> | undefined>;

  templateTokenTypes = signal<TemplateTokenTypes>({}) as Signal<TemplateTokenTypes>;

  availableContainerTypes = signal<string[]>([]) as Signal<string[]>;

  emptyContainerTemplate: ContainerTemplate = {
    name: "",
    container_type: "",
    default: false,
    template_options: {
      tokens: []
    }
  };

  // --- Mocked Methods ---

  getTokenTypesForContainerType = jest.fn((_type: string): string[] => []);

  deleteTemplate = jest.fn((_name: string) => Promise.resolve());
  deleteTemplates = jest.fn((_names: string[]) => Promise.resolve());

  postTemplateEdits = jest.fn((_template: ContainerTemplate) => Promise.resolve(true));
  copyTemplate = jest.fn((_template: ContainerTemplate, _newName: string) => Promise.resolve(true));

  canSaveTemplate = jest.fn((_template: ContainerTemplate): boolean => true);
}
