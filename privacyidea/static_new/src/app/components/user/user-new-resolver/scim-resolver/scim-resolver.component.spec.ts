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
import { ScimResolverComponent } from "./scim-resolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";

describe("ScimResolverComponent", () => {
  let component: ScimResolverComponent;
  let componentRef: ComponentRef<ScimResolverComponent>;
  let fixture: ComponentFixture<ScimResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScimResolverComponent, NoopAnimationsModule]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ScimResolverComponent);
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
      Authserver: component.authServerControl,
      Resourceserver: component.resourceServerControl
    }));
  });

  it("should update controls when data input changes", () => {
    componentRef.setInput("data", {
      Authserver: "http://auth",
      Resourceserver: "http://resource",
      Client: "client1",
      Secret: "secret1",
      Mapping: "{}"
    });

    fixture.detectChanges();

    expect(component.authServerControl.value).toBe("http://auth");
    expect(component.resourceServerControl.value).toBe("http://resource");
    expect(component.clientControl.value).toBe("client1");
    expect(component.secretControl.value).toBe("secret1");
    expect(component.mappingControl.value).toBe("{}");
  });
});
