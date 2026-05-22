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
import { ScimResolverComponent } from "./scim-resolver.component";

describe("ScimResolverComponent", () => {
  let component: ScimResolverComponent;
  let componentRef: ComponentRef<ScimResolverComponent>;
  let fixture: ComponentFixture<ScimResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScimResolverComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ScimResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should expose isValid and getValue", () => {
    expect(typeof component.isValid).toBe("function");
    expect(typeof component.getValue).toBe("function");
  });

  it("should update model when data input changes", () => {
    componentRef.setInput("data", {
      Authserver: "http://auth",
      Resourceserver: "http://resource",
      Client: "client1",
      Secret: "secret1",
      Mapping: "{}"
    });

    fixture.detectChanges();

    expect(component.model().Authserver).toBe("http://auth");
    expect(component.model().Resourceserver).toBe("http://resource");
    expect(component.model().Client).toBe("client1");
    expect(component.model().Secret).toBe("secret1");
    expect(component.model().Mapping).toBe("{}");
  });
});
