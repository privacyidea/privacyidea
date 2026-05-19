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

    expect(component.model().responseMapping).toBe('{"username":"{username}", "userid":"{userid}"}');
  });

  it("should NOT overwrite responseMapping when switching to Advanced mode if it is already set", () => {
    // Initially in Basic mode
    expect(component["basicSettings"]()).toBe(true);
    component.model.update(m => ({ ...m, responseMapping: '{"custom":"mapping"}' }));

    // Switch to Advanced mode
    component["basicSettings"].set(false);
    fixture.detectChanges();

    expect(component.model().responseMapping).toBe('{"custom":"mapping"}');
  });
});
