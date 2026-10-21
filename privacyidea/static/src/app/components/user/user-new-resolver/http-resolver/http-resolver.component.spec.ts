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
import { ComponentRef, DebugElement } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MatCheckbox } from "@angular/material/checkbox";
import { By } from "@angular/platform-browser";
import { ResolverService } from "@services/resolver/resolver.service";
import { MockPiResponse } from "@testing/mock-services";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { touchAll } from "@utils/form-state.utils";
import { of } from "rxjs";
import { HttpConfigComponent } from "./http-config/http-config.component";
import { HttpResolverComponent } from "./http-resolver.component";

describe("HttpResolverComponent", () => {
  let component: HttpResolverComponent;
  let componentRef: ComponentRef<HttpResolverComponent>;
  let fixture: ComponentFixture<HttpResolverComponent>;
  let mockResolverService: MockResolverService;

  beforeEach(async () => {
    mockResolverService = new MockResolverService();
    await TestBed.configureTestingModule({
      imports: [HttpResolverComponent],
      providers: [{ provide: ResolverService, useValue: mockResolverService }]
    }).compileComponents();

    fixture = TestBed.createComponent(HttpResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should fetch defaults when data is empty", () => {
    expect(mockResolverService.getDefaultResolverConfig).toHaveBeenCalledWith("httpresolver");
  });

  it("should apply defaults from server", () => {
    const defaults = {
      endpoint: "http://default-endpoint",
      method: "POST",
      verify_tls: false
    };
    mockResolverService.getDefaultResolverConfig.mockReturnValue(of(MockPiResponse.fromValue(defaults)));

    componentRef.setInput("data", {}); // Ensure it's empty
    fixture.detectChanges();

    expect(component.model().endpoint).toBe("http://default-endpoint");
    expect(component.model().method).toBe("POST");
    expect(component.model().verify_tls).toBe(false);
  });

  it("should expose isValid and getValue", () => {
    expect(typeof component.isValid).toBe("function");
    expect(typeof component.getValue).toBe("function");
  });

  it("should update model when data input changes", () => {
    componentRef.setInput("data", {
      endpoint: "http://test",
      method: "POST",
      attribute_mapping: { username: "user" }
    });

    fixture.detectChanges();

    expect(component.model().endpoint).toBe("http://test");
    expect(component.model().method).toBe("POST");
    expect(component["mappingRows"]()).toContainEqual({
      privacyideaAttr: "username",
      userStoreAttr: "user",
      isCustom: false
    });
  });

  it("should parse boolean and numeric strings from data input", () => {
    // Switch to advanced mode to see baseUrl and other controls
    component["basicSettings"].set(false);
    fixture.detectChanges();

    componentRef.setInput("data", {
      Editable: "1",
      verify_tls: "0",
      timeout: "30"
    });

    fixture.detectChanges();

    expect(component.model().Editable).toBe(true);
    expect(component.model().verify_tls).toBe(false);
    expect(component.model().timeout).toBe(30);
  });

  it("should add and remove mapping rows", () => {
    const initialCount = component["mappingRows"]().length;
    // Simulate selecting an attribute in the last row
    const lastIndex = initialCount - 1;
    component.onPrivacyIdeaAttrChanged(lastIndex, "mobile");

    expect(component["mappingRows"]().length).toBe(initialCount + 1);

    component.removeMappingRow(0);
    expect(component["mappingRows"]().length).toBe(initialCount);
  });

  it("should add a new empty row when the last row's attribute is set", () => {
    const rows = component["mappingRows"]();
    const lastIndex = rows.length - 1;
    expect(rows[lastIndex].privacyideaAttr).toBeNull();

    // Simulate selecting an attribute in the last row
    component.onPrivacyIdeaAttrChanged(lastIndex, "mobile");

    const newRows = component["mappingRows"]();
    expect(newRows.length).toBe(rows.length + 1);
    expect(newRows[newRows.length - 1].privacyideaAttr).toBeNull();
  });

  it("should handle privacyidea custom attribute selection", () => {
    const rows = component["mappingRows"]();
    const index = rows.length - 1;
    component.onPrivacyIdeaAttrChanged(index, component["CUSTOM_ATTR_VALUE"]);

    const updatedRows = component["mappingRows"]();
    expect(updatedRows[index].isCustom).toBe(true);
    expect(updatedRows[index].privacyideaAttr).toBe("");
    // Should have added a new row because it's no longer the placeholder
    expect(updatedRows.length).toBe(rows.length + 1);
    expect(updatedRows[updatedRows.length - 1].privacyideaAttr).toBeNull();
  });

  it("should return correct checkUserPasswordHint based on type", () => {
    // Default type
    expect(component.checkUserPasswordHint()).toBe("Possible tags: {userid} {username} {password}");

    // EntraID type
    componentRef.setInput("type", "entraidresolver");
    fixture.detectChanges();
    expect(component.checkUserPasswordHint()).toBe(
      "Possible tags: {userid} {username} {password} {client_id} {client_credential} {tenant}"
    );

    // Switch back
    componentRef.setInput("type", "httpresolver");
    fixture.detectChanges();
    expect(component.checkUserPasswordHint()).toBe("Possible tags: {userid} {username} {password}");
  });

  it("should preset responseMapping only when switching to Advanced mode and it is empty", () => {
    // Initially in Basic mode
    expect(component["basicSettings"]()).toBe(true);
    expect(component.model().responseMapping).toBe("");

    // Switch to Advanced mode
    component["basicSettings"].set(false);
    fixture.detectChanges();

    expect(component.model().responseMapping).toBe("{\"username\":\"{username}\", \"userid\":\"{userid}\"}");
  });

  it("should NOT overwrite responseMapping when switching to Advanced mode if it is already set", () => {
    // Initially in Basic mode
    expect(component["basicSettings"]()).toBe(true);
    component.model.update((m) => ({ ...m, responseMapping: "{\"custom\":\"mapping\"}" }));

    // Switch to Advanced mode
    component["basicSettings"].set(false);
    fixture.detectChanges();

    expect(component.model().responseMapping).toBe("{\"custom\":\"mapping\"}");
  });

  describe("value posted to the server", () => {
    const REQUEST_CONFIG_KEYS = [
      "config_authorization",
      "config_user_auth",
      "config_get_user_list",
      "config_get_user_by_id",
      "config_get_user_by_name",
      "config_create_user",
      "config_edit_user",
      "config_delete_user"
    ];
    const basicResolver = {
      type: "httpresolver",
      endpoint: "https://userstore.example/users/{userid}",
      method: "GET",
      headers: '{"Content-Type": "application/json"}',
      requestMapping: '{"id": "{userid}"}',
      responseMapping: '{"username": "{username}", "userid": "{userid}"}'
    };

    function specialErrorHandlingCheckbox() {
      return fixture.debugElement
        .queryAll(By.css("mat-checkbox"))
        .find((checkbox) => checkbox.nativeElement.textContent.includes("Special Error Handling"))!;
    }

    it("posts the basic fields and {} for everything else of a basic resolver", () => {
      componentRef.setInput("data", basicResolver);
      fixture.detectChanges();
      const value = component.getValue();
      expect(value["endpoint"]).toBe(basicResolver.endpoint);
      expect(value["responseMapping"]).toBe(basicResolver.responseMapping);
      for (const key of REQUEST_CONFIG_KEYS) {
        expect(value[key]).toEqual({});
      }
      expect(value["attribute_mapping"]).toEqual({});
      expect(value["Editable"]).toBe(false);
      expect(value).not.toHaveProperty("base_url");
      expect(value).not.toHaveProperty("global_headers");
      expect(value).not.toHaveProperty("verify_tls");
    });

    it("posts {} for every request without an endpoint of an advanced resolver", () => {
      componentRef.setInput("data", {
        base_url: "https://userstore.example",
        headers: '{"X-Api-Key": "abc"}',
        config_get_user_by_id: { method: "GET", endpoint: "/users/{userid}" }
      });
      fixture.detectChanges();
      const value = component.getValue();
      expect((value["config_get_user_by_id"] as { endpoint: string }).endpoint).toBe("/users/{userid}");
      for (const key of REQUEST_CONFIG_KEYS.filter((key) => key !== "config_get_user_by_id")) {
        expect(value[key]).toEqual({});
      }
      expect(value["headers"]).toBe('{"X-Api-Key": "abc"}');
      expect(value).not.toHaveProperty("endpoint");
    });

    it("posts the edited global headers as headers", () => {
      componentRef.setInput("data", { base_url: "https://userstore.example", headers: '{"X-Api-Key": "old"}' });
      fixture.detectChanges();
      component.model.update((model) => ({ ...model, global_headers: '{"X-Api-Key": "new"}' }));
      expect(component.getValue()["headers"]).toBe('{"X-Api-Key": "new"}');
    });

    it("posts the user groups of the groups form", () => {
      componentRef.setInput("data", { base_url: "https://userstore.example" });
      fixture.detectChanges();
      component.model.update((model) => ({
        ...model,
        config_get_user_groups: { ...model.config_get_user_groups, active: true, endpoint: "/users/{userid}/groups" }
      }));
      fixture.detectChanges();
      expect(component.getValue()["config_get_user_groups"]).toEqual(
        expect.objectContaining({ active: true, endpoint: "/users/{userid}/groups" })
      );
    });

    it("basic mode: Special Error Handling sets hasSpecialErrorHandler and not Editable", () => {
      componentRef.setInput("data", basicResolver);
      fixture.detectChanges();
      expect(component["basicSettings"]()).toBe(true);

      specialErrorHandlingCheckbox().query(By.css("input")).nativeElement.click();
      fixture.detectChanges();

      expect(component.model().hasSpecialErrorHandler).toBe(true);
      expect(component.model().Editable).toBe(false);
      expect(fixture.nativeElement.textContent).toContain("Response contains (JSON Format)");
      expect(component.getValue()).toEqual(expect.objectContaining({ hasSpecialErrorHandler: true, Editable: false }));
    });

    it("basic mode: a stored hasSpecialErrorHandler is shown as checked", () => {
      componentRef.setInput("data", {
        ...basicResolver,
        // The server returns the stored value as a string
        hasSpecialErrorHandler: "True" as unknown as boolean,
        errorResponse: '{"success": false}'
      });
      fixture.detectChanges();

      expect(component.model().hasSpecialErrorHandler).toBe(true);
      expect(specialErrorHandlingCheckbox().componentInstance.checked).toBe(true);
    });

    it("keeps a response mapping typed in basic mode for a new resolver", () => {
      expect(component["basicSettings"]()).toBe(true);
      component.model.update((model) => ({ ...model, responseMapping: '{"username": "{username}"}' }));
      fixture.detectChanges();
      expect(component.model().responseMapping).toBe('{"username": "{username}"}');
    });
  });
  describe("rules", () => {
    const kinds = (field: { errors(): { kind: string }[] }) => field.errors().map((e) => e.kind);

    const fillBasicMode = () =>
      component.model.update((m) => ({
        ...m,
        endpoint: "https://userstore.example/users/{userid}",
        requestMapping: '{"id": "{userid}"}',
        headers: '{"Content-Type": "application/json"}',
        responseMapping: '{"username": "{username}"}'
      }));

    const useAdvancedMode = () => {
      component["basicSettings"].set(false);
      fixture.detectChanges();
    };

    const errorTexts = () =>
      Array.from<Element>(fixture.nativeElement.querySelectorAll("mat-error")).map((e) => e.textContent);

    describe("basic mode", () => {
      it("requires endpoint, request mapping, headers and response mapping", () => {
        expect(component.isValid()).toBe(false);
        expect(kinds(component.httpForm.endpoint())).toEqual(["required"]);
        expect(kinds(component.httpForm.requestMapping())).toEqual(["required"]);
        expect(kinds(component.httpForm.headers())).toEqual(["required"]);
        expect(kinds(component.httpForm.responseMapping())).toEqual(["required"]);
        expect(component.httpForm.method().errors()).toEqual([]);

        fillBasicMode();
        expect(component.isValid()).toBe(true);
      });

      it("rejects a value made of whitespace", () => {
        fillBasicMode();
        component.model.update((m) => ({ ...m, endpoint: "   " }));
        expect(kinds(component.httpForm.endpoint())).toEqual(["required"]);
        expect(component.isValid()).toBe(false);
      });

      it("requires the error response only with Special Error Handling", () => {
        fillBasicMode();
        expect(component.httpForm.errorResponse().errors()).toEqual([]);

        component.model.update((m) => ({ ...m, hasSpecialErrorHandler: true }));
        expect(kinds(component.httpForm.errorResponse())).toEqual(["required"]);
        expect(component.isValid()).toBe(false);

        component.model.update((m) => ({ ...m, errorResponse: '{"success": false}' }));
        expect(component.isValid()).toBe(true);
      });

      it("does not apply the advanced rules", () => {
        fillBasicMode();
        component.model.update((m) => ({ ...m, base_url: "", timeout: null }));
        expect(component.httpForm.base_url().errors()).toEqual([]);
        expect(component.httpForm.timeout().errors()).toEqual([]);
        expect(component.isValid()).toBe(true);
      });

      it("renders the required messages of the touched fields", async () => {
        expect(errorTexts()).toEqual([]);

        await touchAll(component.httpForm);
        fixture.detectChanges();

        const texts = errorTexts().join(" | ");
        expect(texts).toContain("Endpoint is required.");
        expect(texts).toContain("Request mapping is required.");
        expect(texts).toContain("Headers are required.");
        expect(texts).toContain("Response mapping is required.");
        expect(texts).not.toContain("Response contains");
      });

      it("renders the required message of the error response", async () => {
        component.model.update((m) => ({ ...m, hasSpecialErrorHandler: true }));
        fixture.detectChanges();

        await touchAll(component.httpForm);
        fixture.detectChanges();

        expect(errorTexts().join(" | ")).toContain("Response contains is required.");
      });
    });

    describe("advanced mode", () => {
      beforeEach(() => useAdvancedMode());

      it("requires the base URL and a timeout and ignores the basic fields", () => {
        expect(kinds(component.httpForm.base_url())).toEqual(["required"]);
        expect(component.httpForm.endpoint().errors()).toEqual([]);
        expect(component.httpForm.requestMapping().errors()).toEqual([]);
        expect(component.isValid()).toBe(false);

        component.model.update((m) => ({ ...m, base_url: "https://userstore.example" }));
        expect(component.isValid()).toBe(true);
      });

      it("renders the required message of the base URL", async () => {
        await touchAll(component.httpForm);
        fixture.detectChanges();
        expect(errorTexts().join(" | ")).toContain("Base URL is required.");
      });

      it("requires a timeout", async () => {
        component.model.update((m) => ({ ...m, base_url: "https://userstore.example", timeout: null }));
        expect(kinds(component.httpForm.timeout())).toEqual(["required"]);
        expect(component.isValid()).toBe(false);

        await touchAll(component.httpForm);
        fixture.detectChanges();
        expect(errorTexts().join(" | ")).toContain("Timeout is required.");
      });

      it("reports text the browser cannot parse as a number in the timeout", async () => {
        component.model.update((m) => ({ ...m, base_url: "https://userstore.example" }));
        const timeout = fixture.debugElement.query(By.css("input[type=number]")).nativeElement as HTMLInputElement;
        jest.spyOn(timeout, "validity", "get").mockReturnValue({ badInput: true } as ValidityState);
        timeout.value = "";
        timeout.dispatchEvent(new Event("input"));
        await touchAll(component.httpForm);
        fixture.detectChanges();

        expect(kinds(component.httpForm.timeout())).toContain("parse");
        expect(component.isValid()).toBe(false);
        expect(errorTexts().join(" | ")).toContain("Timeout must be a number.");
      });

      it("keeps a numeric timeout valid", () => {
        component.model.update((m) => ({ ...m, base_url: "https://userstore.example", timeout: 30 }));
        expect(component.httpForm.timeout().errors()).toEqual([]);
        expect(component.getValue()["timeout"]).toBe(30);
      });

      it("does not require the Entra ID fields of another type", () => {
        component.model.update((m) => ({ ...m, base_url: "https://userstore.example" }));
        expect(component.httpForm.tenant().errors()).toEqual([]);
        expect(component.httpForm.client_id().errors()).toEqual([]);
        expect(component.httpForm.client_secret().errors()).toEqual([]);
      });

      it("disables the CA certificate unless the TLS certificate is verified", () => {
        expect(component.httpForm.tls_ca_path().disabled()).toBe(false);

        component.model.update((m) => ({ ...m, verify_tls: false }));
        fixture.detectChanges();

        expect(component.httpForm.tls_ca_path().disabled()).toBe(true);
        const caInput = fixture.debugElement.query(By.css("input[placeholder='/etc/privacyidea/ldap-ca.crt']"));
        expect(caInput.nativeElement.disabled).toBe(true);
      });
    });

    describe("Entra ID", () => {
      beforeEach(() => {
        componentRef.setInput("type", "entraidresolver");
        useAdvancedMode();
        component.model.update((m) => ({ ...m, base_url: "https://graph.microsoft.com/v1.0" }));
      });

      it("requires tenant, client ID and the client secret", () => {
        expect(kinds(component.httpForm.tenant())).toEqual(["required"]);
        expect(kinds(component.httpForm.client_id())).toEqual(["required"]);
        expect(kinds(component.httpForm.client_secret())).toEqual(["required"]);
        expect(component.isValid()).toBe(false);

        component.model.update((m) => ({ ...m, tenant: "tenant", client_id: "client", client_secret: "secret" }));
        expect(component.isValid()).toBe(true);
      });

      it("does not require the client secret for a certificate", () => {
        component.model.update((m) => ({
          ...m,
          tenant: "tenant",
          client_id: "client",
          client_credential_type: "certificate"
        }));
        expect(component.httpForm.client_secret().errors()).toEqual([]);
        expect(component.isValid()).toBe(true);
      });

      it("renders the required messages", async () => {
        await touchAll(component.httpForm);
        fixture.detectChanges();

        const texts = errorTexts().join(" | ");
        expect(texts).toContain("Tenant ID is required.");
        expect(texts).toContain("Client ID is required.");
        expect(texts).toContain("Client secret is required.");
      });

      it("writes the certificate fields typed into the form", () => {
        component.model.update((m) => ({ ...m, client_credential_type: "certificate" }));
        fixture.detectChanges();

        const type = (placeholder: string, value: string) => {
          const input = fixture.debugElement.query(By.css(`input[placeholder='${placeholder}']`)).nativeElement;
          input.value = value;
          input.dispatchEvent(new Event("input"));
        };
        type("/etc/privacyidea/entra.key", "/key.pem");
        type("e.g. 1234567890ABCDEF1234567890ABCDEF12345678", "ABCDEF");

        expect(component.model().client_certificate).toEqual(
          expect.objectContaining({ private_key_file: "/key.pem", certificate_fingerprint: "ABCDEF" })
        );
        expect(component.isDirty()).toBe(true);
      });
    });
  });

  describe("dirty state", () => {
    const inputByPlaceholder = (root: DebugElement, placeholder: string): HTMLInputElement =>
      root.query(By.css(`[placeholder='${placeholder}']`)).nativeElement;

    beforeEach(() => {
      componentRef.setInput("data", {
        base_url: "https://userstore.example",
        config_get_user_list: { method: "GET", endpoint: "/users" },
        config_get_user_groups: { active: false, pi_user_groups_key: "groups", method: "GET", endpoint: "" }
      });
      fixture.detectChanges();
    });

    it("is not dirty after the data is loaded", () => {
      expect(component.isDirty()).toBe(false);
    });

    it("is dirty after typing into a field of a request configuration", () => {
      const configs = fixture.debugElement.queryAll(By.directive(HttpConfigComponent));
      const endpoint = inputByPlaceholder(configs[2], "/users");
      endpoint.value = "/people";
      endpoint.dispatchEvent(new Event("input"));

      expect(component.model().config_get_user_list.endpoint).toBe("/people");
      expect(component.isDirty()).toBe(true);
    });

    it("is dirty after clearing the endpoint of a request configuration", () => {
      const configs = fixture.debugElement.queryAll(By.directive(HttpConfigComponent));
      configs[2].query(By.css("app-clear-button button")).nativeElement.click();

      expect(component.model().config_get_user_list.endpoint).toBe("");
      expect(component.isDirty()).toBe(true);
    });

    it("is dirty after switching on the user groups", () => {
      fixture.debugElement.query(By.css("app-http-groups-attribute mat-slide-toggle button")).nativeElement.click();

      expect(component.model().config_get_user_groups.active).toBe(true);
      expect(component.isDirty()).toBe(true);
    });

    it("is dirty after editing a user store attribute of the mapping", () => {
      const attribute = fixture.debugElement.query(By.css("input[placeholder='e.g. givenname']")).nativeElement;
      attribute.value = "firstName";
      attribute.dispatchEvent(new Event("input"));

      expect(component.model().attribute_mapping).toEqual(expect.objectContaining({ userid: "firstName" }));
      expect(component.isDirty()).toBe(true);
    });

    it("is dirty after removing a mapping row", () => {
      component.removeMappingRow(0);

      expect(component.isDirty()).toBe(true);
    });

    it("is dirty after clearing the base URL", () => {
      fixture.debugElement.query(By.css("app-clearable-input app-clear-button button")).nativeElement.click();
      fixture.detectChanges();

      expect(component.isDirty()).toBe(true);
    });

    it("is dirty after toggling only a checkbox", () => {
      fixture.debugElement
        .queryAll(By.directive(MatCheckbox))
        .find((checkbox) => checkbox.nativeElement.textContent.includes("Verify TLS"))!
        .query(By.css("input"))
        .nativeElement.click();
      fixture.detectChanges();

      expect(component.model().verify_tls).toBe(false);
      expect(component.isDirty()).toBe(true);
    });
  });

  describe("loading request configurations", () => {
    it("merges the stored configurations into the model", () => {
      componentRef.setInput("data", {
        base_url: "https://userstore.example",
        config_get_user_list: { method: "post", endpoint: "/users", headers: { "X-Key": "1" } },
        config_get_user_groups: { active: true, method: "get", endpoint: "/groups" },
        config_user_auth: "not an object" as unknown as undefined
      });
      fixture.detectChanges();

      expect(component.model().config_get_user_list).toEqual(
        expect.objectContaining({ method: "POST", endpoint: "/users", headers: '{"X-Key":"1"}' })
      );
      expect(component.model().config_get_user_groups).toEqual(
        expect.objectContaining({ active: true, method: "GET", endpoint: "/groups", pi_user_groups_key: "groups" })
      );
      expect(component.model().config_user_auth.endpoint).toBe("");
    });
  });
});
