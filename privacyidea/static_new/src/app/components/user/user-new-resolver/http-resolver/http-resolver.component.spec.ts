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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { HttpResolverComponent } from "./http-resolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";

describe("HttpResolverComponent", () => {
  let component: HttpResolverComponent;
  let componentRef: ComponentRef<HttpResolverComponent>;
  let fixture: ComponentFixture<HttpResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HttpResolverComponent, NoopAnimationsModule]
    })
      .compileComponents();

    fixture = TestBed.createComponent(HttpResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should expose controls via signal", () => {
    const controls = component.controls();
    expect(controls).toEqual(expect.objectContaining({
      endpoint: component.endpointControl,
      method: component.methodControl
    }));
  });

  it("should update controls when data input changes", () => {
    componentRef.setInput("data", {
      endpoint: "http://test",
      method: "POST",
      attribute_mapping: { "username": "user" }
    });

    fixture.detectChanges();

    expect(component.endpointControl.value).toBe("http://test");
    expect(component.methodControl.value).toBe("POST");
    expect(component["mappingRows"]()).toContainEqual({
      privacyideaAttr: "username",
      userStoreAttr: "user",
      isCustom: false
    });
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
    expect(component.checkUserPasswordHint()).toBe("Possible tags: {userid} {username} {password} {client_id} {client_credential} {tenant}");

    // Switch back
    componentRef.setInput("type", "httpresolver");
    fixture.detectChanges();
    expect(component.checkUserPasswordHint()).toBe("Possible tags: {userid} {username} {password}");
  });

});
