import { TestBed } from "@angular/core/testing";
import { ContainerTemplateService } from "./container-template.service";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { ContainerService } from "../container/container.service";
import { ContentService } from "../content/content.service";
import { AuthService } from "../auth/auth.service";
import { NotificationService } from "../notification/notification.service";
import { ROUTE_PATHS } from "../../route_paths";
import { environment } from "../../../environments/environment";
import { provideHttpClient } from "@angular/common/http";
import { ContainerTemplate } from "../container/container.service";
import { MockContainerService, MockContentService, MockNotificationService } from "../../../testing/mock-services";
import { MockAuthService } from "../../../testing/mock-services/mock-auth-service";
import { last, lastValueFrom, of } from "rxjs";

describe("ContainerTemplateService", () => {
  let service: ContainerTemplateService;
  let httpMock: HttpTestingController;
  let authServiceMock: MockAuthService;
  let contentServiceMock: MockContentService;
  let containerServiceMock: MockContainerService;
  let notificationServiceMock: MockNotificationService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        ContainerTemplateService,
        { provide: AuthService, useClass: MockAuthService },
        { provide: ContentService, useClass: MockContentService },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: NotificationService, useClass: MockNotificationService }
      ]
    });
    service = TestBed.inject(ContainerTemplateService);
    httpMock = TestBed.inject(HttpTestingController);
    authServiceMock = TestBed.inject(AuthService) as unknown as MockAuthService;
    contentServiceMock = TestBed.inject(ContentService) as unknown as MockContentService;
    containerServiceMock = TestBed.inject(ContainerService) as unknown as MockContainerService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    authServiceMock.actionAllowed.mockReturnValue(true);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  describe("templatesResource", () => {
    beforeEach(() => {
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_CREATE);
      authServiceMock.actionAllowed.mockReturnValue(true);
    });

    afterEach(() => {
      // This is for the templateTokentypesResource which is also triggered
      const req = httpMock.match(`${environment.proxyUrl}/container/template/tokentypes`);
      if (req.length > 0 && !req[0].cancelled) {
        req[0].flush({ result: { value: {} } });
      }
    });

    it("should fetch templates when on the correct route and with permission", async () => {
      // Setup
      TestBed.flushEffects();

      // Execute
      const req = httpMock.expectOne(`${service.containerTemplateBaseUrl}?container_type=test-type`);
      req.flush({ result: { value: { templates: [{ name: "template1" }] } } });
      TestBed.flushEffects();
      await lastValueFrom(of(null).pipe(last()));

      // Assertion
      const value = service.templatesResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value?.templates).toBeDefined();
      expect(value?.result?.value?.templates).toEqual([{ name: "template1" }]);
      expect(service.templates()).toEqual([{ name: "template1" }]);
    });

    it("should not fetch templates if action is not allowed", async () => {
      // Setup / Execute
      authServiceMock.actionAllowed.mockReturnValue(false);
      TestBed.flushEffects();

      // Assertion
      httpMock.expectNone(`${service.containerTemplateBaseUrl}?container_type=test-type`);
      const value = service.templatesResource.value();
      expect(value).toBeUndefined();
      expect(service.templates()).toEqual([]);
    });

    it("should not fetch templates if not on the correct route", async () => {
      // Setup / Execute
      contentServiceMock.routeUrl.set("/wrong/route");
      TestBed.flushEffects();
      await lastValueFrom(of(null).pipe(last()));

      // Assertion
      httpMock.expectNone(`${service.containerTemplateBaseUrl}?container_type=test-type`);
      const value = service.templatesResource.value();
      expect(value).toBeUndefined();
      expect(service.templates()).toEqual([]);
    });
  });

  describe("templateTokentypesResource", () => {
    beforeEach(() => {
      // Set up conditions for templatesResource to be fetched as well, as it's triggered by default
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_CREATE);
      authServiceMock.actionAllowed.mockReturnValue(true);
    });

    afterEach(() => {
      // This is for the templateTokentypesResource which is also triggered
      const req = httpMock.match(`${service.containerTemplateBaseUrl}`);
      if (req.length > 0 && !req[0].cancelled) {
        req[0].flush({ result: { value: {} } });
      }
    });

    it("should fetch token types", async () => {
      // Setup
      TestBed.flushEffects();

      // Execute
      const tokenTypesReq = httpMock.expectOne(`${environment.proxyUrl}/container/template/tokentypes`);
      const mockTokenTypes = { type1: { description: "Type 1", token_types: ["token1"] } };
      tokenTypesReq.flush({ result: { value: mockTokenTypes } });
      TestBed.flushEffects();
      await lastValueFrom(of(null).pipe(last()));

      // Assertion
      const value = service.templateTokentypesResource.value();
      expect(value).toBeDefined();
      expect(value?.result?.value).toEqual(mockTokenTypes);
      expect(service.templateTokenTypes()).toEqual(mockTokenTypes);
    });

    it("should not fetch token types if not on the correct route", async () => {
      // Setup / Execute
      contentServiceMock.routeUrl.set("/wrong/route");
      TestBed.flushEffects();

      // Assertion
      httpMock.expectNone(`${environment.proxyUrl}/container/template/tokentypes`);
      const value = service.templateTokentypesResource.value();
      expect(value).toBeUndefined();
      expect(service.templateTokenTypes()).toEqual({});
    });
    it("should not fetch token types if action is not allowed", async () => {
      // Setup / Execute
      authServiceMock.actionAllowed.mockReturnValue(false);
      TestBed.flushEffects();

      // Assertion
      httpMock.expectNone(`${environment.proxyUrl}/container/template/tokentypes`);
      const value = service.templateTokentypesResource.value();
      expect(value).toBeUndefined();
      expect(service.templateTokenTypes()).toEqual({});
    });
  });

  describe("getTokenTypesForContainerType", () => {
    beforeEach(() => {
      // Set up conditions for both resources to be fetched
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_CREATE);
      authServiceMock.actionAllowed.mockReturnValue(true);
    });

    afterEach(() => {
      // This is for the templateTokentypesResource, and templatesResource which are both triggered
      const req = [
        ...httpMock.match(`${environment.proxyUrl}/container/template/tokentypes`),
        ...httpMock.match(`${service.containerTemplateBaseUrl}`)
      ];
      if (req.length > 0 && !req[0].cancelled) {
        req[0].flush({ result: { value: {} } });
      }
    });

    it("should return token types for a given container type", async () => {
      // Setup
      TestBed.flushEffects();

      // Flush initial requests
      const templatesReq = httpMock.expectOne(`${service.containerTemplateBaseUrl}`);
      templatesReq.flush({ result: { value: { templates: [] } } });
      const tokenTypesReq = httpMock.expectOne(`${environment.proxyUrl}/container/template/tokentypes`);
      const mockTokenTypes = { type1: { description: "Type 1", token_types: ["token1", "token2"] } };
      tokenTypesReq.flush({ result: { value: mockTokenTypes } });

      TestBed.flushEffects();
      await lastValueFrom(of(null).pipe(last()));

      // Assertion
      expect(service.getTokenTypesForContainerType("type1")).toEqual(["token1", "token2"]);
    });

    it("should return an empty array for a non-existent container type", async () => {
      // Setup
      TestBed.flushEffects();

      // Flush initial requests
      const templatesReq = httpMock.expectOne(`${service.containerTemplateBaseUrl}`);
      templatesReq.flush({ result: { value: { templates: [] } } });
      const tokenTypesReq = httpMock.expectOne(`${environment.proxyUrl}/container/template/tokentypes`);
      const mockTokenTypes = { type1: { description: "Type 1", token_types: ["token1", "token2"] } };
      tokenTypesReq.flush({ result: { value: mockTokenTypes } });

      TestBed.flushEffects();
      await lastValueFrom(of(null).pipe(last()));

      // Assertion
      expect(service.getTokenTypesForContainerType("non-existent")).toEqual([]);
    });

    it("should return only the requested container type's token types", async () => {
      // Setup
      TestBed.flushEffects();

      // Flush initial requests
      const templatesReq = httpMock.expectOne(`${service.containerTemplateBaseUrl}`);
      templatesReq.flush({ result: { value: { templates: [] } } });
      const tokenTypesReq = httpMock.expectOne(`${environment.proxyUrl}/container/template/tokentypes`);
      const mockTokenTypes = {
        type1: { description: "Type 1", token_types: ["token1", "token2"] },
        type2: { description: "Type 2", token_types: ["token3"] }
      };
      tokenTypesReq.flush({ result: { value: mockTokenTypes } });

      TestBed.flushEffects();
      await lastValueFrom(of(null).pipe(last()));

      // Assertion
      expect(service.getTokenTypesForContainerType("type2")).toEqual(["token3"]);
    });
  });

  describe("deleteTemplate", () => {
    it("should send a DELETE request and show success notification", async () => {
      const templateName = "template-to-delete";
      service.deleteTemplate(templateName);

      const req = httpMock.expectOne(`/container/template/${templateName}`);
      expect(req.request.method).toBe("DELETE");
      req.flush({});

      await lastValueFrom(of(null).pipe(last())); // wait for subscribe callback

      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Successfully deleted template.");
    });

    it("should handle error on delete and show error notification", async () => {
      const templateName = "template-to-delete";
      service.deleteTemplate(templateName);

      const req = httpMock.expectOne(`/container/template/${templateName}`);
      req.flush({ result: { error: { message: "Error message" } } }, { status: 500, statusText: "Server Error" });

      await lastValueFrom(of(null).pipe(last())); // wait for subscribe callback

      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Failed to delete template. Error message");
    });

    it("should check permissions before deleting", async () => {
      // Setup
      authServiceMock.actionAllowed.mockReturnValue(false);
      TestBed.flushEffects();

      // Execute
      const templateName = "template-to-delete";
      service.deleteTemplate(templateName);
      httpMock.expectNone(`/container/template/${templateName}`);

      await lastValueFrom(of(null).pipe(last())); // wait for subscribe callback
      expect(authServiceMock.actionAllowed).toHaveBeenCalledWith("container_template_delete");
      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(
        "You are not allowed to delete container templates."
      );
    });
  });

  describe("postTemplateEdits", () => {
    const template: ContainerTemplate = {
      name: "test-template",
      container_type: "generic",
      default: false,
      template_options: {
        tokens: [],
        options: undefined
      }
    };

    beforeEach(() => {
      // Set up conditions for both resources to be fetched and flush them
      contentServiceMock.routeUrl.set(ROUTE_PATHS.TOKENS_CONTAINERS_CREATE);
      authServiceMock.actionAllowed.mockReturnValue(true);
      TestBed.flushEffects();
      const reqs = httpMock.match(() => true);
      reqs.forEach((req) => req.flush({ result: { value: {} } }));
    });

    it("should send a POST request and show success notification", async () => {
      const promise = service.postTemplateEdits(template);

      const req = httpMock.expectOne(
        `${environment.proxyUrl}/container/${template.container_type}/template/${template.name}`
      );
      expect(req.request.method).toBe("POST");
      req.flush({});

      await promise;
      await lastValueFrom(of(null).pipe(last())); // wait for subscribe callback

      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith(`Successfully saved template edits.`);
    });

    it("should handle error on post and show error notification", async () => {
      const promise = service.postTemplateEdits(template);

      const req = httpMock.expectOne(
        `${environment.proxyUrl}/container/${template.container_type}/template/${template.name}`
      );
      req.flush({ result: { error: { message: "Error message" } } }, { status: 500, statusText: "Server Error" });

      await promise;
      await lastValueFrom(of(null).pipe(last())); // wait for subscribe callback

      expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Failed to save template edits. Error message");
    });
  });

  describe("canSaveTemplate", () => {
    let validTemplate: ContainerTemplate;
    beforeEach(() => {
      validTemplate = {
        name: "valid-template",
        container_type: "generic",
        default: false,
        template_options: {
          tokens: [{ type: "token1", genkey: false, hashlib: "", otplen: 6, timeStep: 0, user: false }],
          options: undefined
        }
      };
    });
    it("should return true on valid template", () => {
      expect(service.canSaveTemplate(validTemplate)).toBe(true);
    });
    it("should return false on empty name", () => {
      const invalidTemplate = { ...validTemplate, name: "   " };
      expect(service.canSaveTemplate(invalidTemplate)).toBe(false);
    });
    it("should return false on empty container type", () => {
      const invalidTemplate: ContainerTemplate = { ...validTemplate, container_type: "" };
      expect(service.canSaveTemplate(invalidTemplate)).toBe(false);
    });
    it("should return false on empty token list", () => {
      const invalidTemplate = { ...validTemplate, template_options: { ...validTemplate.template_options, tokens: [] } };
      expect(service.canSaveTemplate(invalidTemplate)).toBe(false);
    });
  });

  describe("ContainerTemplateService additional tests", () => {

    describe("Side effects", () => {
      it("should call templatesResource.reload on successful deletion");
      it("should call templatesResource.reload on successful template edit");
    });
  
    describe("Error handling", () => {
      it("should show a generic error notification on delete if error response contains no message");
      it("should show a generic error notification on post if error response contains no message");
      it("should handle http error when fetching templatesResource");
      it("should handle http error when fetching templateTokentypesResource");
      it("should handle malformed success response when fetching templatesResource");
    });
  
    describe("Computed signals", () => {
      describe("availableContainerTypes", () => {
        it("should be empty initially");
        it("should contain the keys from a successful token types fetch");
        it("should be empty if token types fetch fails");
      });
    });
  
    describe("Request variations", () => {
      it("should fetch templates without query parameter if no container type is selected");
    });
  
    describe("Authentication", () => {
      it("should not make any http requests if user is not logged in");
    });
  
  });
});