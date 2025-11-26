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
