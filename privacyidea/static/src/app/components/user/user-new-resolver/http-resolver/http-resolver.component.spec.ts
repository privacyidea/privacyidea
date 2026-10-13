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
import { ComponentRef } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { ResolverService } from "@services/resolver/resolver.service";
import { MockPiResponse } from "@testing/mock-services";
import { MockResolverService } from "@testing/mock-services/mock-resolver-service";
import { of } from "rxjs";
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
      component.userGroupsModel.update((groups) => ({ ...groups, active: true, endpoint: "/users/{userid}/groups" }));
      fixture.detectChanges();
      expect(component.getValue()["config_get_user_groups"]).toEqual(
        expect.objectContaining({ active: true, endpoint: "/users/{userid}/groups" })
      );
    });

    it("basic mode: Special Error Handling sets hasSpecialErrorHandler and not Editable", () => {
      componentRef.setInput("data", basicResolver);
      fixture.detectChanges();
      expect(component["basicSettings"]()).toBe(true);

      specialErrorHandlingCheckbox().triggerEventHandler("change", { checked: true });
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
});
