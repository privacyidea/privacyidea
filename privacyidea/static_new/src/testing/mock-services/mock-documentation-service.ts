import { signal, WritableSignal } from "@angular/core";
import { DocumentationServiceInterface } from "../../app/services/documentation/documentation.service";

export class MockDocumentationService implements DocumentationServiceInterface {
  openDocumentation = jest.fn();
  getVersionUrl = jest.fn().mockReturnValue("mock-version-url");
  getFallbackUrl = jest.fn().mockReturnValue("mock-fallback-url");
  checkFullUrl = jest.fn().mockResolvedValue(true);
  checkPageUrl = jest.fn().mockResolvedValue("mock-page-url");
  openDocumentationPage = jest.fn().mockResolvedValue(true);

  policyActionSectionId: WritableSignal<string | null> = signal(null);
  policyActionDocumentation: WritableSignal<{ actionDocu: string[]; actionNotes: string[] } | null> = signal(null);
}
